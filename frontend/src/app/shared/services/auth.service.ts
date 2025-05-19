import { Injectable } from '@angular/core';
import { CanActivate, Router, ActivatedRouteSnapshot } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import {catchError, firstValueFrom, map, of} from 'rxjs';
import { environment } from '../../../environments/environment';

export interface IUser {
  id: string;
  email: string;
  avatarUrl?: string;
  profile_image_url?: string;
  gender?: string;
  role_band: string;
  role_title: string;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: IUser;
}

const defaultPath = '/login-form';
const defaultUser = {
  email: 'sandra@example.com',
  avatarUrl: 'https://js.devexpress.com/Demos/WidgetsGallery/JSDemos/images/employees/06.png'
};

@Injectable()
export class AuthService {
  private _user: IUser | null = null;
  private API_URL = environment.apiUrl;

  private isTokenExpired(token: string): boolean {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
      }).join(''));

      const { exp } = JSON.parse(jsonPayload);

      const currentTime = Math.floor(Date.now() / 1000);
      return exp < currentTime;
    } catch {
      return true;
    }
  }

  private validateToken(): boolean {
    const token = localStorage.getItem('user_token');
    if (!token) {
      return false;
    }
    return !this.isTokenExpired(token);
  }

  get loggedIn(): boolean {
    if (!this._user || !localStorage.getItem('user_token')) {
      return false;
    }
    return this.validateToken();
  }

  get user(): IUser | null {
    return this._user;
  }

  get isAdmin(): boolean {
    return this._user?.role_band === 'Admin' || this._user?.role_title === 'Admin';
  }

  get isHR(): boolean {
    return this._user?.role_band === 'HR' || this._user?.role_title === 'HR';
  }

  get isManager(): boolean {
    return this._user?.role_band === 'Manager' || this._user?.role_title === 'Manager';
  }

  private _lastAuthenticatedPath: string = defaultPath;
  set lastAuthenticatedPath(value: string) {
    this._lastAuthenticatedPath = value;
  }

  async getUserById(userId: string): Promise<any> {
    try {
      const response = await firstValueFrom(
        this.http.get(`${this.API_URL}/users/${userId}`)
      );
      return response;
    } catch (error) {
      console.error('Error fetching user:', error);
      return null;
    }
  }

  constructor(private router: Router, private http: HttpClient,) {
    const storedUser = localStorage.getItem('current_user');
    if (storedUser) {
      this._user = JSON.parse(storedUser);
      // Check token validity on initialization
      if (!this.validateToken()) {
        this.logOut();
      }
    }
  }

  async logIn(email: string, password: string) {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);

    try {
      const response = await firstValueFrom(
        this.http.post<LoginResponse>(`${this.API_URL}/auth/login`, formData)
      );

      // Set default avatarUrl if user doesn't have a profile image
      if (!response.user.profile_image_url && !response.user.avatarUrl) {
        // Use gender-specific default avatars if gender is available
        if (response.user.gender === 'Male') {
          response.user.avatarUrl = 'https://cdn-icons-png.flaticon.com/512/847/847969.png';
        } else if (response.user.gender === 'Female') {
          response.user.avatarUrl = 'https://cdn-icons-png.flaticon.com/512/4140/4140047.png';
        } else {
          // Default neutral avatar
          response.user.avatarUrl = 'https://cdn-icons-png.flaticon.com/512/847/847969.png';
        }
      }

      this._user = response.user;
      localStorage.setItem('current_user', JSON.stringify(response.user));
      localStorage.setItem('user_token', response.access_token);

      // Redirect admin/HR/manager users to leaves page
      const target = this.isAdmin || this.isHR || this.isManager
        ? '/admin/leaves'
        : (this._lastAuthenticatedPath || '/dashboard');

      await this.router.navigateByUrl(target);

      return {
        isOk: true,
        data: response
      };
    }
    catch (error: any) {
      // Clear any existing auth data
      this.logOut();

      return {
        isOk: false,
        message: error.error?.detail || "Authentication failed"
      };
    }
  }

  async getUser() {
    try {
      return {
        isOk: true,
        data: this._user
      };
    }
    catch {
      return {
        isOk: false,
        data: null
      };
    }
  }

  async createAccount(email: string, password: string) {
    try {
      this.router.navigate(['/create-account']);
      return {
        isOk: true
      };
    }
    catch {
      return {
        isOk: false,
        message: "Failed to create account"
      };
    }
  }

  async changePassword(email: string, recoveryCode: string) {
    try {
      return {
        isOk: true
      };
    }
    catch {
      return {
        isOk: false,
        message: "Failed to change password"
      }
    }
  }

  async resetPassword(email: string) {
    try {
      return {
        isOk: true
      };
    }
    catch {
      return {
        isOk: false,
        message: "Failed to reset password"
      };
    }
  }

  async logOut() {
    this._user = null;
    localStorage.removeItem('current_user');
    localStorage.removeItem('user_token');
    this.router.navigate(['/login-form']);
  }
}

@Injectable()
export class AuthGuardService implements CanActivate {
  constructor(private router: Router, private authService: AuthService) { }

  canActivate(route: ActivatedRouteSnapshot): boolean {
    const isLoggedIn = this.authService.loggedIn;
    const isAuthForm = [
      'login-form',
      'reset-password',
      'create-account',
      'change-password/:recoveryCode'
    ].includes(route.routeConfig?.path || defaultPath);

    if (isLoggedIn && isAuthForm) {
      this.authService.lastAuthenticatedPath = defaultPath;
      this.router.navigate([defaultPath]);
      return false;
    }

    if (!isLoggedIn && !isAuthForm) {
      this.router.navigate(['/login-form']);
      return false;
    }

    if (route.routeConfig?.path?.startsWith('admin') && !this.authService.isAdmin) {
      this.router.navigate(['/dashboard']);
      return false;
    }

    if (isLoggedIn) {
      this.authService.lastAuthenticatedPath = route.routeConfig?.path || defaultPath;
    }

    return isLoggedIn || isAuthForm;
  }
}
