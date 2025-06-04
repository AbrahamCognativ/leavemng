import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, firstValueFrom } from 'rxjs';
import { User } from '../../models/user.model';
import { environment } from '../../../environments/environment';

export interface IUser {
  id: string;
  email: string;
  avatarUrl?: string;
  name?: string;
  role_band?: string;
  role_title?: string;
  org_unit_id?: string;
  manager_id?: string;
  passport_or_id_number?: string;
  profile_image_url?: string;
  extra_metadata?: any;
  created_at?: string;
  gender?: string;
  is_active?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class UserService {
  private apiUrl = `${environment.apiUrl}/users`;

  constructor(private http: HttpClient) {}

  // Observable-based methods
  getUsers(): Observable<User[]> {
    return this.http.get<User[]>(this.apiUrl);
  }

  getUser(id: string): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/${id}`);
  }

  updateUser(id: string, user: Partial<User>): Observable<User> {
    return this.http.put<User>(`${this.apiUrl}/${id}`, user);
  }

  createUser(user: Partial<User>): Observable<User> {
    return this.http.post<User>(this.apiUrl, user);
  }

  deleteUser(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }

  // Promise-based methods for backward compatibility
  async getUserById(id: string): Promise<IUser | null> {
    try {
      return await firstValueFrom(this.http.get<IUser>(`${this.apiUrl}/${id}`));
    } catch (error) {
      console.error('Failed to fetch user:', error);
      return null;
    }
  }

  async getAllUsers(): Promise<IUser[]> {
    try {
      return await firstValueFrom(this.http.get<IUser[]>(this.apiUrl));
    } catch (error) {
      console.error('Failed to fetch all users:', error);
      return [];
    }
  }

  async updateUserAsync(user: IUser): Promise<IUser | null> {
    try {
      return await firstValueFrom(this.http.put<IUser>(`${this.apiUrl}/${user.id}`, user));
    } catch (error) {
      console.error('Failed to update user:', error);
      return null;
    }
  }

  async deleteUserAsync(userId: string): Promise<boolean> {
    try {
      await firstValueFrom(this.http.delete(`${this.apiUrl}/${userId}`));
      return true;
    } catch (error) {
      console.error('Failed to delete user:', error);
      return false;
    }
  }
}
