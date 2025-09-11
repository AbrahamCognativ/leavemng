// leave.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, retry } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

// Define interfaces for our data models
interface UserDetails {
  email: string;
  full_name?: string;
  [key: string]: any;
}

interface LeaveRequestData {
  user_id?: string;
  employee_email?: string;
  employee_name?: string;
  [key: string]: any;
}

@Injectable({
  providedIn: 'root'
})
export class LeaveService {
  private apiUrl = environment.apiUrl;
  private userCache = new Map<string, UserDetails>();
  private cacheExpiry = 5 * 60 * 1000; // 5 minutes cache
  private lastFetchTime = 0;

  constructor(private http: HttpClient) {}

  // Get all leave requests with enriched user data
  // Get all approved leave requests
  async getAllApprovedLeaves(): Promise<any[]> {
    try {
      const leaveRequests = await this.http.get<any[]>(`${this.apiUrl}/leave`)
        .pipe(
          retry(1),
          catchError(this.handleError)
        ).toPromise() as any[];
      
      if (!leaveRequests || !Array.isArray(leaveRequests)) {
        console.error('Invalid leave requests data:', leaveRequests);
        return [];
      }
      
      // Filter for approved leaves only
      const approvedLeaves = leaveRequests.filter(request => {
        const isApproved = request.status && request.status.toLowerCase() === 'approved';
        return isApproved;
      });
      
      if (!approvedLeaves.length) {
        console.warn('No approved leaves found');
        return [];
      }

      // Only refresh user cache if it's empty or expired
      const now = Date.now();
      if (this.userCache.size === 0 || (now - this.lastFetchTime) > this.cacheExpiry) {
        await this.refreshUserCache(approvedLeaves);
        this.lastFetchTime = now;
      }

      // Enrich leave requests with cached user details
      const enrichedLeaves = this.enrichLeaveRequests(approvedLeaves);
      return enrichedLeaves;

    } catch (error) {
      console.error('Error in getAllApprovedLeaves:', error);
      return [];
    }
  }

  async getLeaveRequests(): Promise<any[]> {
    try {
      // Get all leave requests
      const leaveRequests = await this.http.get<any[]>(`${this.apiUrl}/leave`)
        .pipe(
          retry(1),
          catchError(this.handleError)
        ).toPromise() as any[];

      if (!leaveRequests) return [];

      // Only refresh user cache if it's empty or expired
      const now = Date.now();
      if (this.userCache.size === 0 || (now - this.lastFetchTime) > this.cacheExpiry) {
        await this.refreshUserCache(leaveRequests);
        this.lastFetchTime = now;
      }

      // Enrich leave requests with cached user details
      return this.enrichLeaveRequests(leaveRequests);

    } catch (error) {
      console.error('Error in getLeaveRequests:', error);
      return [];
    }
  }

  private async refreshUserCache(leaveRequests: LeaveRequestData[]): Promise<void> {
    // Get unique user IDs and filter out undefined/null values
    const userIds = Array.from(new Set(
      leaveRequests
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
        console.error(`Error fetching user ${userId}:`, error);
        // Add a fallback user to cache to prevent repeated failed requests
        this.userCache.set(userId, {
          email: `${userId}@example.com`,
          full_name: `User ${userId.substring(0, 8)}`
        });
      }
    });

    await Promise.all(userPromises);
  }

  private enrichLeaveRequests(requests: LeaveRequestData[]): LeaveRequestData[] {
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

  // Get leave request details
  async getLeaveRequestDetails(requestId: string): Promise<any> {
    return this.http.get<any>(`${this.apiUrl}/leave/${requestId}`)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  // Get leave data (balances + requests) for a user
  async getUserLeave(userId: string): Promise<any> {
    return this.http.get<any>(`${this.apiUrl}/users/${userId}/leave`)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  // Get leave types
  async getLeaveTypes(): Promise<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/leave-types`)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<any[]>;
  }

  // creates a leave type
  async createLeaveType(leaveType: any): Promise<any> {
    return this.http.post<any>(`${this.apiUrl}/leave-types`, leaveType)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  // updates a leave type
  async updateLeaveType(id: string, leaveType: any): Promise<any> {
    return this.http.put<any>(`${this.apiUrl}/leave-types/${id}`, leaveType)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  // deletes a leave type
  async deleteLeaveType(id: string): Promise<any> {
    return this.http.delete<any>(`${this.apiUrl}/leave-types/${id}`)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  // Upload file for leave request
  async uploadFile(leaveRequestId: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file); // Backend expects 'file', not 'document'
    
    const url = `${this.apiUrl}/files/upload/${leaveRequestId}`;
    
    try {
      const response = await this.http.post<any>(url, formData)
        .pipe(
          retry(1),
          catchError((error) => {
            console.error('File upload error detail:', error);
            return this.handleError(error);
          })
        ).toPromise();
      
      return response;
    } catch (error) {
      console.error('Error in uploadFile try-catch:', error);
      throw error;
    }
  }

  // Create leave request (JSON data only)
  async createLeaveRequest(data: any): Promise<any> {  
    // The auth interceptor will automatically add the Authorization header
    return this.http.post<any>(`${this.apiUrl}/leave`, data)
      .pipe(
        catchError((error) => {
          console.error('Leave request creation error:', error);
          return this.handleError(error);
        })
      ).toPromise() as Promise<any>;
  }

  async updateLeaveRequest(leaveId: string, data: any): Promise<any> { 
    const url = `${this.apiUrl}/leave/${leaveId}`;
    const headers = { 'Content-Type': 'application/json' };
    
    try {
      const response = await this.http.patch<any>(url, data, { headers })
        .pipe(
          // No retry for PATCH - we don't want to risk double-updating
          catchError((error) => {
            console.error('Leave request update error detail:', error);
            return this.handleError(error);
          })
        ).toPromise();
      
      return response;
    } catch (error) {
      console.error('Error in updateLeaveRequest try-catch:', error);
      throw error;
    }
  }

  // Delete leave document
  async deleteLeaveDocument(leaveId: string, documentId: string): Promise<any> {
    if (!leaveId || !documentId) {
      console.error('Invalid parameters for document deletion', { leaveId, documentId });
      throw new Error('Invalid parameters for document deletion');
    }
    
    // Ensure we have clean IDs without any extra spaces
    const cleanLeaveId = leaveId.trim();
    const cleanDocId = documentId.trim();
    
    const url = `${this.apiUrl}/files/delete/${cleanLeaveId}/${cleanDocId}`;
    
    try {
      const options = {
        headers: this.getAuthHeaders()
      };
      
      const response = await this.http.delete<any>(url, options)
        .pipe(
          catchError((error) => {
            console.error('Document delete error detail:', error);
            return this.handleError(error);
          })
        ).toPromise();
      
      return response;
    } catch (error) {
      console.error('Error in deleteLeaveDocument try-catch:', error);
      throw error;
    }
  }
  
  // Using the getAuthHeaders method defined below

  // Download leave document
  async downloadLeaveDocument(leaveId: string, documentId: string): Promise<Blob> {
    return this.http.get(`${this.apiUrl}/leave/${leaveId}/documents/${documentId}/download`, {
      responseType: 'blob'
    }).pipe(
      retry(1),
      catchError(this.handleError)
    ).toPromise() as Promise<Blob>;
  }
  
  // Get leave policies
  async getLeavePolicies(): Promise<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/leave-policy`)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<any[]>;
  }

  // Create leave policy
  async createLeavePolicy(policy: any): Promise<any> {
    return this.http.post<any>(`${this.apiUrl}/leave-policy`, policy)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  // Update leave policy
  async updateLeavePolicy(id: string, policy: any): Promise<any> {
    return this.http.put<any>(`${this.apiUrl}/leave-policy/${id}`, policy)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  // Delete leave policy
  async deleteLeavePolicy(id: string): Promise<any> {
    return this.http.delete<any>(`${this.apiUrl}/leave-policy/${id}`)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  // Get organization units
  async getOrgUnits(): Promise<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/org`)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<any[]>;
  }

  // Fully update leave request (uses PUT)
  async updateFullLeaveRequest(requestId: string, leaveData: any): Promise<any> {
    return this.http.put<any>(`${this.apiUrl}/leave/${requestId}`, leaveData)
      .pipe(
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  // Approve leave request
  async approveLeaveRequest(requestId: string, approvalNote?: string): Promise<any> {
    const formData = new FormData();
    if (approvalNote) {
      formData.append('approval_note', approvalNote);
    }
    
    return this.http.patch<any>(`${this.apiUrl}/leave/${requestId}/approve`, formData)
      .pipe(
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  // Reject leave request
  async rejectLeaveRequest(requestId: string, approvalNote?: string): Promise<any> {
    const formData = new FormData();
    if (approvalNote) {
      formData.append('approval_note', approvalNote);
    }
    
    return this.http.patch<any>(`${this.apiUrl}/leave/${requestId}/reject`, formData)
      .pipe(
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  // Upload leave document
  async uploadLeaveDocument(requestId: string, file: File): Promise<any> {
    // Create form data object with the file
    const formData = new FormData();
    
    // IMPORTANT: The parameter name 'file' must match what the backend expects
    // This is defined in the FastAPI endpoint as 'file: UploadFile = File(...)'
    formData.append('file', file, file.name);
    
    // Don't set Content-Type header - browser will set it with correct boundary
    try {
      const response = await this.http.post<any>(`${this.apiUrl}/files/upload/${requestId}`, formData, {
        // Important: Don't set Content-Type here, let the browser set it with the correct boundary
        // But we do need to include the Authorization header
        headers: this.getAuthHeaders()
      }).toPromise();
      
      return response;
    } catch (error) {
      console.error('Document upload error:', error);
      throw error;
    }
  }
  
  // Helper method to get auth headers
  private getAuthHeaders(): Record<string, string> {
    const token = localStorage.getItem('token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  // Get leave documents
  async getLeaveDocuments(requestId: string): Promise<any[]> {
    const url = `${this.apiUrl}/files/list/${requestId}`;
    
    try {
      const response = await this.http.get<any[]>(url)
        .pipe(
          retry(1),
          catchError((error) => {
            console.error('Get documents error detail:', error);
            return this.handleError(error);
          })
        ).toPromise();
      
      return response || [];
    } catch (error) {
      console.error('Error in getLeaveDocuments try-catch:', error);
      return [];
    }
  }

  // Download leave document from files API
  async downloadLeaveDocumentFromFiles(requestId: string, documentId: string): Promise<Blob> {
    if (!requestId || !documentId) {
      console.error('Invalid parameters for document download', { requestId, documentId });
      throw new Error('Invalid parameters for document download');
    }
    
    // Ensure we have clean IDs without any extra spaces
    const cleanRequestId = requestId.trim();
    const cleanDocId = documentId.trim();
    
    const url = `${this.apiUrl}/files/download/${cleanRequestId}/${cleanDocId}`;
    
    try {
      // Set appropriate headers for blob download
      const headers = new HttpHeaders({
        'Accept': 'application/octet-stream'
      });
      
      const response = await this.http.get(url, {
        headers: headers,
        responseType: 'blob',
        observe: 'response'
      }).pipe(
        catchError((error) => {
          console.error('Document download error detail:', error);
          return this.handleError(error);
        })
      ).toPromise();
      
      if (!response || !response.body) {
        console.error('Empty response received');
        throw new Error('Empty response received from server');
      }
      
      return response.body;
    } catch (error) {
      console.error('Error in downloadLeaveDocumentFromFiles try-catch:', error);
      throw error;
    }
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

    console.error(errorMessage);
    return throwError(() => ({
      error: {
        detail: errorMessage
      }
    }));
  }
}
