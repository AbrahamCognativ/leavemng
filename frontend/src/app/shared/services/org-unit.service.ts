import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, retry } from 'rxjs/operators';

export interface OrgUnit {
  id: string;
  name: string;
  description?: string;
  parent_id?: string;
  created_at: string;
  updated_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class OrgUnitService {
  private apiUrl = 'http://localhost:8000/api/v1';

  constructor(private http: HttpClient) {}

  // Get all organization units
  async getOrgUnits(): Promise<OrgUnit[]> {
    return this.http.get<OrgUnit[]>(`${this.apiUrl}/org`)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<OrgUnit[]>;
  }

  // Create organization unit
  async createOrgUnit(orgUnit: Partial<OrgUnit>): Promise<OrgUnit> {
    return this.http.post<OrgUnit>(`${this.apiUrl}/org`, orgUnit)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<OrgUnit>;
  }

  // Update organization unit
  async updateOrgUnit(id: string, orgUnit: Partial<OrgUnit>): Promise<OrgUnit> {
    return this.http.put<OrgUnit>(`${this.apiUrl}/org/${id}`, orgUnit)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<OrgUnit>;
  }

  // Delete organization unit
  async deleteOrgUnit(id: string): Promise<any> {
    return this.http.delete<any>(`${this.apiUrl}/org/${id}`)
      .pipe(
        retry(1),
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
