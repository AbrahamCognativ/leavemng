import { Injectable } from '@angular/core';
import {HttpClient, HttpHeaders} from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
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

@Injectable()
export class UserService {
  private API_URL = environment.apiUrl;

  constructor(private http: HttpClient) {}


  async getUserById(id: string): Promise<IUser | null> {
    const token = this.getToken();

    if (!token) {
      console.error("Token not found");
      return null;
    }

    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });

    try {
      const user = await firstValueFrom(
        this.http.get<IUser>(`${this.API_URL}/users/${id}`, { headers: {
          'Authorization': `Bearer ${token}`
        } })
      );
      return user;
    } catch (error) {
      console.error('Failed to fetch user:', error);
      return null;
    }
  }

  async getAllUsers(): Promise<IUser[]> {
    try {
      const users = await firstValueFrom(
        this.http.get<IUser[]>(`${this.API_URL}/users`)
      );
      return users;
    } catch (error) {
      console.error('Failed to fetch all users:', error);
      return [];
    }
  }

  async updateUser(user: IUser): Promise<IUser | null> {
    try {
      const updated = await firstValueFrom(
        this.http.patch<IUser>(`${this.API_URL}/users/${user.id}`, user)
      );
      return updated;
    } catch (error) {
      console.error('Failed to update user:', error);
      return null;
    }
  }

  async deleteUser(userId: string): Promise<boolean> {
    try {
      await firstValueFrom(
        this.http.delete(`${this.API_URL}/users/${userId}`)
      );
      return true;
    } catch (error) {
      console.error('Failed to delete user:', error);
      return false;
    }
  }

  getToken(): string | null {
    return localStorage.getItem('user_token');
  }

}
