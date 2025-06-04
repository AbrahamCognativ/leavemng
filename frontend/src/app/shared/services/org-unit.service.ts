import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, retry, map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { OrgNode } from '../../models/org.model';
import { AuthService } from './auth.service';

export interface Manager {
  id: string;
  name: string;
  email: string;
  role_title: string;
}

export interface OrgUnit {
  id: string;
  name: string;
  parent_unit_id?: string;
  children?: OrgUnit[];
}

export interface OrgUnitTree extends OrgUnit {
  managers: Manager[];
  children: OrgUnitTree[];
}

export interface TreeItem {
  id: string;
  name: string;
  type?: 'unit' | 'role';
  is_manager?: boolean;
  users?: any[];
  managers?: any[];
  children?: TreeItem[];
  parent_unit_id?: string;
}

@Injectable({
  providedIn: 'root'
})
export class OrgUnitService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // Get all organization units
  getOrgUnits(): Observable<OrgUnit[]> {
    return this.http.get<OrgUnit[]>(`${this.apiUrl}/org`)
      .pipe(
        retry(1),
        catchError(this.handleError)
      );
  }

  // Get organization tree structure
  async getOrgTree(): Promise<OrgUnitTree[]> {
    return this.http.get<OrgUnitTree[]>(`${this.apiUrl}/org/tree`)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<OrgUnitTree[]>;
  }

  // Create organization unit
  createOrgUnit(orgUnit: Partial<OrgUnit>): Observable<OrgUnit> {
    return this.http.post<OrgUnit>(`${this.apiUrl}/org`, orgUnit)
      .pipe(
        retry(1),
        catchError(this.handleError)
      );
  }

  // Update organization unit
  updateOrgUnit(id: string, orgUnit: Partial<OrgUnit>): Observable<OrgUnit> {
    return this.http.put<OrgUnit>(`${this.apiUrl}/org/${id}`, orgUnit)
      .pipe(
        retry(1),
        catchError(this.handleError)
      );
  }

  // Delete organization unit
  deleteOrgUnit(id: string): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/org/${id}`)
      .pipe(
        retry(1),
        catchError(this.handleError)
      );
  }

  // Get organization chart structure
  getOrgChart(): Observable<TreeItem[]> {
    return this.http.get<TreeItem[]>(`${this.apiUrl}/org/chart/tree`)
      .pipe(
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
