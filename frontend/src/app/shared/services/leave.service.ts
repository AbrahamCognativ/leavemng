// leave.service.ts
import { Injectable } from '@angular/core';
import {HttpClient, HttpErrorResponse} from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, retry } from 'rxjs/operators';
//import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class LeaveService {
  // Define your API base URL here
  private apiUrl = 'http://localhost:8000/api/v1';

  constructor(private http: HttpClient) {}

  // Get all leave requests
  async getLeaveRequests(): Promise<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/leave`)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<any[]>;
  }

  // Get leave request details
  async getLeaveRequestDetails(requestId: string): Promise<any> {
    return this.http.get<any>(`${this.apiUrl}/leave/${requestId}`)
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

  // Create leave request
  async createLeaveRequest(leaveData: any): Promise<any> {
    return this.http.post<any>(`${this.apiUrl}/leave`, leaveData)
      .pipe(
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  // Update leave request
  async updateLeaveRequest(requestId: string, leaveData: any): Promise<any> {
    return this.http.put<any>(`${this.apiUrl}/leave/${requestId}`, leaveData)
      .pipe(
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  // Approve leave request
  async approveLeaveRequest(requestId: string): Promise<any> {
    return this.http.patch<any>(`${this.apiUrl}/leave/${requestId}/approve`, {})
      .pipe(
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  // Upload leave document
  async uploadLeaveDocument(requestId: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<any>(`${this.apiUrl}/files/upload/${requestId}`, formData)
      .pipe(
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  // Get leave documents
  async getLeaveDocuments(requestId: string): Promise<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/files/list/${requestId}`)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<any[]>;
  }

  // Download leave document
  async downloadLeaveDocument(requestId: string, documentId: string): Promise<Blob> {
    return this.http.get(`${this.apiUrl}/files/download/${requestId}/${documentId}`, {
      responseType: 'blob'
    }).pipe(
      catchError(this.handleError)
    ).toPromise() as Promise<Blob>;
  }

  // Delete leave document
  async deleteLeaveDocument(requestId: string, documentId: string): Promise<any> {
    return this.http.delete<any>(`${this.apiUrl}/files/delete/${requestId}/${documentId}`)
      .pipe(
        catchError(this.handleError)
      ).toPromise() as Promise<any>;
  }

  private handleError(error: HttpErrorResponse) {
    let errorMessage = 'An unknown error occurred';

    if (error.error instanceof ErrorEvent) {
      // Client-side error
      errorMessage = `Error: ${error.error.message}`;
    } else {
      // Server-side error
      errorMessage = `Error Code: ${error.status}\nMessage: ${error.message}`;
    }

    console.error(errorMessage);
    return throwError(() => new Error(errorMessage));
  }
}
