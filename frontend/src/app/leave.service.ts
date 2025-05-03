import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import {catchError, map, Observable, of} from 'rxjs';
import {Leave, LeaveBalance, NotificationConfig} from './models/leave.model';

@Injectable({
  providedIn: 'root'
})
export class LeaveService {
  private apiUrl = 'http://localhost:3000/api/leaves';

  constructor(private http: HttpClient) { }

  getCurrentEmployeeId(): number {
    // test
    return 1001;
  }

  getEmployeeLeaveBalances(employeeId: number): Observable<LeaveBalance[]> {
    return this.http.get<LeaveBalance[]>(`${this.apiUrl}/balances/${employeeId}`)
      .pipe(
        catchError(this.handleError<LeaveBalance[]>('getEmployeeLeaveBalances', []))
      );
  }
  // Get all leaves
  getAllLeaves(): Observable<Leave[]> {
    return this.http.get<Leave[]>(this.apiUrl);
  }

  // Get leave by ID
  getLeave(id: number): Observable<Leave> {
    return this.http.get<Leave>(`${this.apiUrl}/${id}`);
  }

  // Create new leave request
  createLeave(leave: Leave): Observable<Leave> {
    return this.http.post<Leave>(this.apiUrl, leave);
  }

  // Update leave request
  updateLeave(id: number, leave: Leave): Observable<Leave> {
    return this.http.put<Leave>(`${this.apiUrl}/${id}`, leave);
  }

  // Delete leave request
  deleteLeave(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }

  // Get leave statistics
  getLeaveStatistics(): Observable<any> {
    return this.http.get(`${this.apiUrl}/statistics`);
  }

  private handleError<T>(operation = 'operation', result?: T) {
    return (error: any): Observable<T> => {
      console.error(`${operation} failed: ${error.message}`);
      // Let the app keep running by returning an empty result
      return of(result as T);
    };
  }

  showNotification(config: NotificationConfig): void {
    // For simplicity, we're using an alert
    console.log(`${config.type.toUpperCase()}: ${config.message}`);
    alert(config.message);
  }
  calculateWorkingDays(startDate: Date, endDate: Date): Observable<number> {
    // considering weekends and holidays
    return this.http.post<{days: number}>(`${this.apiUrl}/calculate-days`, {
      startDate,
      endDate
    }).pipe(
      map(response => response.days),
      catchError(() => {
        // Fallback calculation if API fails
        const start = new Date(startDate);
        const end = new Date(endDate);
        let days = 0;
        const current = new Date(start);

        while (current <= end) {
          const dayOfWeek = current.getDay();
          if (dayOfWeek !== 0 && dayOfWeek !== 6) {
            days++;
          }
          current.setDate(current.getDate() + 1);
        }

        return of(days);
      })
    );
  }

}
