import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, retry } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

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

  // Get organization tree structure
  async getOrgTree(): Promise<OrgUnitTree[]> {
    return this.http.get<OrgUnitTree[]>(`${this.apiUrl}/org/tree`)
      .pipe(
        retry(1),
        catchError(this.handleError)
      ).toPromise() as Promise<OrgUnitTree[]>;
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
