import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, retry, map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { OrgNode } from '../../models/org.model';
import { AuthService } from './auth.service';

export interface OrgUnit {
  id: string;
  name: string;
  parent_unit_id?: string;
  children?: OrgUnit[];
}

@Injectable({
  providedIn: 'root'
})
export class OrgUnitService {
  private apiUrl = environment.apiUrl;

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

  // Get organization chart
  getOrgChart(): Observable<OrgNode[]> {
    const headers = this.getAuthHeaders();
    console.log('Getting org chart data from API with headers:', headers);
    // Use responseType: 'json' with the generic type OrgNode[] and parse the response
    return this.http.get(`${this.apiUrl}/org/chart/tree`, { 
      headers, 
      responseType: 'text' 
    }).pipe(
      map(response => {
        // Parse the text response manually
        console.log('Raw response:', response);
        try {
          const parsedData = JSON.parse(response) as OrgNode[];
          console.log('Successfully parsed org chart data:', parsedData);
          return parsedData;
        } catch (error) {
          console.error('Error parsing org chart response:', error);
          return [];
        }
      }),
      retry(1),
      catchError(this.handleError)
    );
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

  // Helper method to get auth headers
  private getAuthHeaders(): Record<string, string> {
    const token = localStorage.getItem('token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }
}
