import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { IUser } from './auth.service';

@Injectable({
  providedIn: 'root'
})
export class UserStateService {
  private userSubject = new BehaviorSubject<IUser | null>(null);
  public user$ = this.userSubject.asObservable();

  constructor() {
    // Initialize with user from localStorage
    this.loadUserFromStorage();
  }

  private loadUserFromStorage(): void {
    try {
      const rawUser = localStorage.getItem('current_user');
      if (rawUser) {
        const user = JSON.parse(rawUser);
        this.userSubject.next(user);
      }
    } catch (error) {
      console.error('Error loading user from storage:', error);
    }
  }

  getCurrentUser(): IUser | null {
    return this.userSubject.value;
  }

  updateUser(user: IUser): void {
    // Update the BehaviorSubject
    this.userSubject.next(user);
    
    // Update localStorage
    localStorage.setItem('current_user', JSON.stringify(user));
  }

  updateUserProfileImage(imageUrl: string): void {
    const currentUser = this.getCurrentUser();
    if (currentUser) {
      const updatedUser = {
        ...currentUser,
        profile_image_url: imageUrl,
        avatarUrl: imageUrl // Keep both for backward compatibility
      };
      this.updateUser(updatedUser);
    }
  }

  getProfileImageSrc(user?: IUser | null): string {
    const currentUser = user || this.getCurrentUser();
    
    // First try to use the profile_image_url
    if (currentUser?.profile_image_url) {
      return currentUser.profile_image_url;
    }
    
    // Then try to use avatarUrl as fallback
    if (currentUser?.avatarUrl) {
      return currentUser.avatarUrl;
    }
    
    // Use gender-specific default avatars if gender is available
    if (currentUser?.gender === 'Male') {
      return 'https://cdn-icons-png.flaticon.com/512/847/847969.png';
    } else if (currentUser?.gender === 'Female') {
      return 'https://cdn-icons-png.flaticon.com/512/4140/4140047.png';
    }
    
    // Default fallback
    return 'https://cdn-icons-png.flaticon.com/512/847/847969.png';
  }

  clearUser(): void {
    this.userSubject.next(null);
    localStorage.removeItem('current_user');
  }
}
