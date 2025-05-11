import { Injectable } from '@angular/core';
import { CanActivate, Router, ActivatedRouteSnapshot } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import {catchError, firstValueFrom, map, of} from 'rxjs';

export interface IUser {
  id: string;
  email: string;
  avatarUrl?: string;
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
  private API_URL = 'http://localhost:8000/api/v1';

  get loggedIn(): boolean {
    return !!this._user;
  }

  get user(): IUser | null {
    return this._user;
  }

  get isAdmin(): boolean {
    return this._user?.role_band === 'HR' || this._user?.role_band === 'Admin' || 
           this._user?.role_title === 'HR' || this._user?.role_title === 'Admin';
  }

  private _lastAuthenticatedPath: string = defaultPath;
  set lastAuthenticatedPath(value: string) {
    this._lastAuthenticatedPath = value;
  }

  constructor(private router: Router, private http: HttpClient,) {
    const storedUser = localStorage.getItem('current_user');
    if (storedUser) {
      this._user = JSON.parse(storedUser);
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
      this._user = response.user;
      localStorage.setItem('current_user', JSON.stringify(response.user));
      localStorage.setItem('user_token', response.access_token);
      const target = this._lastAuthenticatedPath || '/dashboard';
      await this.router.navigateByUrl(target);

      return {
        isOk: true,
        data: response
      };
    }
    catch {
      return {
        isOk: false,
        message: "Authentication failed"
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
