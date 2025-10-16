import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';
import { NextOfKinContact, NextOfKinCreate, NextOfKinUpdate } from '../../models/next-of-kin.model';

@Injectable({
  providedIn: 'root'
})
export class NextOfKinService {
  private apiUrl = `${environment.apiUrl}/next-of-kin`;

  constructor(private http: HttpClient) {}

  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('user_token') || '';
    return new HttpHeaders({
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    });
  }

  /**
   * Get all next of kin contacts for the current user
   */
  getNextOfKin(): Observable<NextOfKinContact[]> {
    return this.http.get<NextOfKinContact[]>(this.apiUrl, {
      headers: this.getAuthHeaders()
    });
  }

  /**
   * Get next of kin contacts for a specific user (Admin/HR/Manager only)
   */
  getUserNextOfKin(userId: string): Observable<NextOfKinContact[]> {
    return this.http.get<NextOfKinContact[]>(`${this.apiUrl}/user/${userId}`, {
      headers: this.getAuthHeaders()
    });
  }

  /**
   * Create a new next of kin contact
   */
  createNextOfKin(contact: NextOfKinCreate): Observable<NextOfKinContact> {
    return this.http.post<NextOfKinContact>(this.apiUrl, contact, {
      headers: this.getAuthHeaders()
    });
  }

  /**
   * Update an existing next of kin contact
   */
  updateNextOfKin(id: string, contact: NextOfKinUpdate): Observable<NextOfKinContact> {
    return this.http.put<NextOfKinContact>(`${this.apiUrl}/${id}`, contact, {
      headers: this.getAuthHeaders()
    });
  }

  /**
   * Delete a next of kin contact
   */
  deleteNextOfKin(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`, {
      headers: this.getAuthHeaders()
    });
  }


  /**
   * Promise-based methods for backward compatibility
   */
  async getNextOfKinAsync(): Promise<NextOfKinContact[]> {
    try {
      return await firstValueFrom(this.getNextOfKin());
    } catch (error) {
      console.error('Failed to fetch next of kin contacts:', error);
      return [];
    }
  }

  async createNextOfKinAsync(contact: NextOfKinCreate): Promise<NextOfKinContact | null> {
    try {
      return await firstValueFrom(this.createNextOfKin(contact));
    } catch (error) {
      console.error('Failed to create next of kin contact:', error);
      return null;
    }
  }

  async updateNextOfKinAsync(id: string, contact: NextOfKinUpdate): Promise<NextOfKinContact | null> {
    try {
      return await firstValueFrom(this.updateNextOfKin(id, contact));
    } catch (error) {
      console.error('Failed to update next of kin contact:', error);
      return null;
    }
  }

  async deleteNextOfKinAsync(id: string): Promise<boolean> {
    try {
      await firstValueFrom(this.deleteNextOfKin(id));
      return true;
    } catch (error) {
      console.error('Failed to delete next of kin contact:', error);
      return false;
    }
  }

}
