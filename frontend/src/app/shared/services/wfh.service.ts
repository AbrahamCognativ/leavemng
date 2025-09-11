import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, retry } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

// Define interfaces for WFH data models
interface UserDetails {
  email: string;
  full_name?: string;
  [key: string]: any;
}

interface WFHRequestData {
  user_id?: string;
  employee_email?: string;
  employee_name?: string;
  [key: string]: any;
}

@Injectable({
  providedIn: 'root'
})
export class WFHService {
  private apiUrl = environment.apiUrl;
  private userCache = new Map<string, UserDetails>();
  private cacheExpiry = 5 * 60 * 1000; // 5 minutes cache
  private lastFetchTime = 0;

  constructor(private http: HttpClient) {}

  // Get all WFH requests
  async getWFHRequests(): Promise<any[]> {
    try {
      const wfhRequests = await this.http.get<any[]>(`${this.apiUrl}/wfh`)
        .pipe(
          retry(1),
          catchError(this.handleError)
        ).toPromise() as any[];

      return wfhRequests || [];
    } catch (error) {
      return [];
    }
  }

  // Get all approved WFH requests
  async getAllApprovedWFHRequests(): Promise<any[]> {
    try {
      const wfhRequests = await this.http.get<any[]>(`${this.apiUrl}/wfh`)
        .pipe(
          retry(1),
          catchError(this.handleError)
        ).toPromise() as any[];
      
      if (!wfhRequests || !Array.isArray(wfhRequests)) {
        return [];
      }
      
      // Filter for approved WFH requests only
      return wfhRequests.filter(request => {
        const isApproved = request.status && request.status.toLowerCase() === 'approved';
        return isApproved;
      });

    } catch (error) {
      return [];
    }
  }

  private async refreshUserCache(wfhRequests: WFHRequestData[]): Promise<void> {
    // Get unique user IDs and filter out undefined/null values
    const userIds = Array.from(new Set(
      wfhRequests
        .map(req => req.user_id)
        .filter((id): id is string => !!id)
    ));
    
    if (userIds.length === 0) return;
    
    // Only fetch users that aren't in cache
    const usersToFetch = userIds.filter(id => !this.userCache.has(id));
    if (usersToFetch.length === 0) return;
    
    // Fetch user details in parallel
    const userPromises = usersToFetch.map(async (userId: string) => {
      try {
        const user = await this.http.get<UserDetails>(`${this.apiUrl}/users/${userId}`)
          .pipe(catchError(this.handleError))
          .toPromise();
        
        if (user) {
          this.userCache.set(userId, {
            email: user.email,
            full_name: user.full_name || `User ${userId.substring(0, 8)}`
          });
        }
      } catch (error) {
        // Add a fallback user to cache to prevent repeated failed requests
        this.userCache.set(userId, {
          email: `${userId}@example.com`,
          full_name: `User ${userId.substring(0, 8)}`
        });
      }
    });

    await Promise.all(userPromises);
  }

  private enrichWFHRequests(requests: WFHRequestData[]): WFHRequestData[] {
    return requests.map(request => {
      if (!request.user_id) {
        return {
          ...request,
          employee_email: 'unknown@example.com',
          employee_name: 'Unknown User'
        };
      }
      
      const user = this.userCache.get(request.user_id) || {
        email: `${request.user_id}@example.com`,
        full_name: `User ${request.user_id.substring(0, 8)}`
      };
      
      return {
        ...request,
        employee_email: user.email,
        employee_name: user.full_name
      };
    });
  }

  // Clear cache (can be called on logout or when needed)
  clearUserCache(): void {
    this.userCache.clear();
    this.lastFetchTime = 0;
  }

  // Get WFH request details
  async getWFHRequestDetails(requestId: string): Promise<any> {
    return this.http.get<any>(`${this.apiUrl}/wfh/${requestId}`)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  // Create WFH request (JSON data only)
  async createWFHRequest(data: any): Promise<any> {  
    // The auth interceptor will automatically add the Authorization header
    return this.http.post<any>(`${this.apiUrl}/wfh`, data)
      .pipe(
        catchError((error) => {
          return this.handleError(error);
        })
      ).toPromise() as Promise<any>;
  }

  async updateWFHRequest(wfhId: string, data: any): Promise<any> { 
    const url = `${this.apiUrl}/wfh/${wfhId}`;
    const headers = { 'Content-Type': 'application/json' };
    
    try {
      const response = await this.http.patch<any>(url, data, { headers })
        .pipe(
          // No retry for PATCH - we don't want to risk double-updating
          catchError((error) => {
            return this.handleError(error);
          })
        ).toPromise();
      
      return response;
    } catch (error) {
      throw error;
    }
  }

  // Approve WFH request
  async approveWFHRequest(requestId: string, approvalNote?: string): Promise<any> {
    const formData = new FormData();
    if (approvalNote) {
      formData.append('approval_note', approvalNote);
    }
    
    return this.http.patch<any>(`${this.apiUrl}/wfh/${requestId}/approve`, formData)
      .pipe(
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  // Reject WFH request
  async rejectWFHRequest(requestId: string, approvalNote?: string): Promise<any> {
    const formData = new FormData();
    if (approvalNote) {
      formData.append('approval_note', approvalNote);
    }
    
    return this.http.patch<any>(`${this.apiUrl}/wfh/${requestId}/reject`, formData)
      .pipe(
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  // Delete WFH request
  async deleteWFHRequest(requestId: string): Promise<any> {
    return this.http.delete<any>(`${this.apiUrl}/wfh/${requestId}`)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  // Error handler for HTTP requests
  handleError(error: HttpErrorResponse) {
    let errorMessage = 'An unknown error occurred';

    if (error.error instanceof ErrorEvent) {
      // Client-side error
      errorMessage = `Error: ${error.error.message}`;
    } else {
      // Server-side error
      if (error.error && typeof error.error === 'object' && 'detail' in error.error) {
        errorMessage = error.error.detail;
      } else {
        errorMessage = `Error Code: ${error.status}\nMessage: ${error.message}`;
      }
    }

    return throwError(() => ({
      error: {
        detail: errorMessage
      }
    }));
  }
}