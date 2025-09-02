import { Injectable } from '@angular/core';
import { IUser } from './auth.service';

@Injectable({
  providedIn: 'root'
})
export class UserbackService {
  private isInitialized = false;

  constructor() {}

  /**
   * Initialize Userback (called from main.ts)
   */
  initialize(): void {
    this.isInitialized = true;
  }

  /**
   * Update Userback with current user information
   * Call this when user logs in
   */
  updateUser(user: IUser): void {
    if (!this.isInitialized || !this.isUserbackAvailable()) {
      return;
    }

    try {
      (window as any).Userback('identify', {
        id: user.id,
        info: {
          name: user.email.split('@')[0], // Use email prefix as name
          email: user.email,
          role: user.role_band || 'User',
          title: user.role_title || 'Employee',
          gender: user.gender || 'Not specified'
        }
      });
    } catch (error) {
      console.warn('Failed to update Userback user:', error);
    }
  }

  /**
   * Clear user information from Userback
   * Call this when user logs out
   */
  clearUser(): void {
    if (!this.isInitialized || !this.isUserbackAvailable()) {
      return;
    }

    try {
      (window as any).Userback('identify', null);
    } catch (error) {
      console.warn('Failed to clear Userback user:', error);
    }
  }

  /**
   * Show Userback widget
   */
  show(): void {
    if (!this.isInitialized || !this.isUserbackAvailable()) {
      return;
    }

    try {
      (window as any).Userback('show');
    } catch (error) {
      console.warn('Failed to show Userback widget:', error);
    }
  }

  /**
   * Hide Userback widget
   */
  hide(): void {
    if (!this.isInitialized || !this.isUserbackAvailable()) {
      return;
    }

    try {
      (window as any).Userback('hide');
    } catch (error) {
      console.warn('Failed to hide Userback widget:', error);
    }
  }

  /**
   * Check if Userback is available and initialized
   */
  isAvailable(): boolean {
    return this.isInitialized && this.isUserbackAvailable();
  }

  /**
   * Private method to check if Userback is available on window
   */
  private isUserbackAvailable(): boolean {
    return typeof (window as any).Userback === 'function';
  }
}