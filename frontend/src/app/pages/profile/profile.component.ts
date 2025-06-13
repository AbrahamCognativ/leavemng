import {Component, OnInit, OnDestroy, ViewChild, ElementRef} from '@angular/core';
import {DxFormModule} from 'devextreme-angular/ui/form';
import {DxButtonModule} from 'devextreme-angular/ui/button';
import {DxFileUploaderModule} from 'devextreme-angular/ui/file-uploader';
import {DxTextBoxModule} from 'devextreme-angular/ui/text-box';
import {CommonModule} from '@angular/common';
import {HttpClient, HttpClientModule, HttpHeaders} from '@angular/common/http';
import {AuthService} from '../../shared/services';
import { environment } from '../../../environments/environment';
import { UserStateService } from '../../shared/services/user-state.service';
import { Subscription } from 'rxjs';

interface Employee {
  id: string;
  name: string;
  email: string;
  passport_or_id_number: string;
  manager_id: string | null;
  role_band: string;
  role_title: string;
  gender?: string;
  profile_image_url?: string;
  avatarUrl?: string;
  org_unit_id?: string | null;
  extra_metadata?: any;
  token?: string;
  [key: string]: any;
}

interface FileUploaderEvent {
  request: {
    response: string;
  };
  [key: string]: any;
}

@Component({
  templateUrl: 'profile.component.html',
  styleUrls: [ './profile.component.scss' ],
  standalone: true,
  imports: [DxFormModule, DxButtonModule, DxFileUploaderModule, DxTextBoxModule, CommonModule, HttpClientModule]
})

export class ProfileComponent implements OnInit, OnDestroy {
  employee: Employee = {} as Employee;
  colCountByScreen: object;
  isEditing: boolean = false;
  originalEmployee: Employee = {} as Employee;
  baseUrl: string = environment.apiUrl;
  basePlainUrl: string = environment.apiBaseUrl
  isLoading: boolean = false;
  uploadUrl: string = '';
  @ViewChild('fileInput') fileInput!: ElementRef;
  
  // Image state management
  private originalImageUrl: string = '';
  private tempImageFile: File | null = null;
  private tempImageUrl: string = '';
  
  // Password change properties
  passwordData = {
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  };
  isChangingPassword: boolean = false;
  passwordSuccessMessage: string = '';
  passwordErrorMessage: string = '';
  passwordPattern: RegExp = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
  
  private userSubscription: Subscription | null = null;

  constructor(
    private http: HttpClient, 
    private authService: AuthService,
    private userStateService: UserStateService
  ) {
    this.colCountByScreen = {
      xs: 1,
      sm: 2,
      md: 3,
      lg: 4
    };
  }
  
  ngOnInit(): void {
    this.refreshUserData();
    
    // Subscribe to user state changes
    this.userSubscription = this.userStateService.user$.subscribe(user => {
      if (user && user.id === this.employee.id) {
        // Update profile image if it changed from another component
        if (user.profile_image_url !== this.employee.profile_image_url) {
          this.employee.profile_image_url = user.profile_image_url;
        }
      }
    });
  }

  ngOnDestroy(): void {
    if (this.userSubscription) {
      this.userSubscription.unsubscribe();
    }
  }

  private getAuthToken(): string {
    try {
      const rawUser = localStorage.getItem('current_user');
      if (rawUser) {
        const parsedUser = JSON.parse(rawUser);
        return parsedUser?.token || '';
      }
    } catch (error) {
      console.error('Error getting auth token:', error);
    }
    return '';
  }
  
  /**
   * Helper method to format API URLs with the correct version
   */
  getApiUrl(endpoint: string): string {
    // Remove leading slash if present
    if (endpoint.startsWith('/')) {
      endpoint = endpoint.substring(1);
    }
    return `${this.baseUrl}/${endpoint}`;
  }
  
  // For password confirmation validation
  getComparePassword = () => {
    return this.passwordData.newPassword;
  }
  
  // Change password functionality
  changePassword(): void {
    // Reset messages
    this.passwordSuccessMessage = '';
    this.passwordErrorMessage = '';
    
    // Basic validation
    if (!this.passwordData.currentPassword || !this.passwordData.newPassword || !this.passwordData.confirmPassword) {
      this.passwordErrorMessage = 'All password fields are required.';
      return;
    }
    
    if (this.passwordData.newPassword !== this.passwordData.confirmPassword) {
      this.passwordErrorMessage = 'New passwords do not match.';
      return;
    }
    
    if (!this.passwordPattern.test(this.passwordData.newPassword)) {
      this.passwordErrorMessage = 'Password must be at least 8 characters and include uppercase, lowercase, number, and special character.';
      return;
    }
    
    this.isChangingPassword = true;
    
    // Get auth token
    const token = this.getAuthToken();
    
    const changePasswordUrl = this.getApiUrl(`auth/change-password`);
    
    this.http.post(changePasswordUrl, {
      current_password: this.passwordData.currentPassword,
      new_password: this.passwordData.newPassword
    }, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    }).subscribe({
      next: () => {
        this.passwordSuccessMessage = 'Password changed successfully!';
        this.passwordErrorMessage = '';
        // Reset form
        this.passwordData = {
          currentPassword: '',
          newPassword: '',
          confirmPassword: ''
        };
        this.isChangingPassword = false;
      },
      error: (error: any) => {
        this.passwordErrorMessage = error.error?.detail || 'Failed to change password. Please try again.';
        this.passwordSuccessMessage = '';
        this.isChangingPassword = false;
      }
    });
  }
  
  /**
   * Helper method to format image URLs correctly
   */
  formatImageUrl(url: string): string {
    if (!url) return '';
    
    // If it's already a full URL, return as is
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url;
    }
    
    // If it starts with /uploads, prepend the base URL
    if (url.startsWith('/uploads')) {
      return `${this.basePlainUrl}${url}`;
    }
    
    // If it doesn't start with /, add it
    if (!url.startsWith('/')) {
      url = '/' + url;
    }
    
    return `${this.basePlainUrl}${url}`;
  }
  
  /**
   * Refresh user data from the API
   */
  refreshUserData(): void {
    const currentUser = this.userStateService.getCurrentUser();
    if (!currentUser?.id) return;
    
    this.http.get(this.getApiUrl(`users/${currentUser.id}`), {
      headers: this.getAuthToken() ? { Authorization: `Bearer ${this.getAuthToken()}` } : {}
    }).subscribe({
      next: (userData: any) => {
        // Update employee data with fresh API data
        this.employee = {
          ...this.employee,
          ...userData,
          profile_image_url: userData.profile_image_url ? this.formatImageUrl(userData.profile_image_url) : ''
        };
        
        // Store original data for cancel functionality
        this.originalEmployee = { ...this.employee };
        this.originalImageUrl = this.employee.profile_image_url || '';
        
        // Update local storage with fresh data
        const updatedUser = { ...currentUser, ...userData };
        if (userData.profile_image_url) {
          updatedUser.profile_image_url = this.formatImageUrl(userData.profile_image_url);
        }
        this.userStateService.updateUser(updatedUser);
      },
      error: (error: any) => {
        console.error('Failed to refresh user data:', error);
      }
    });
  }
  
  /**
   * Toggle edit mode on/off
   */
  toggleEdit(): void {
    if (this.isEditing) {
      // Cancel editing - revert all changes
      this.employee = { ...this.originalEmployee };
      this.tempImageFile = null;
      this.tempImageUrl = '';
    } else {
      // Store current state as original
      this.originalEmployee = { ...this.employee };
      this.originalImageUrl = this.employee.profile_image_url || '';
    }
    this.isEditing = !this.isEditing;
  }
  
  /**
   * Save changes to the user profile
   */
  saveChanges(): void {
    this.isLoading = true;
    
    // Prepare user data for update (only editable fields)
    const updateData = {
      name: this.employee.name,
      passport_or_id_number: this.employee.passport_or_id_number,
      gender: this.employee.gender
    };
    
    // First update user data using PATCH method to match backend
    this.http.patch(this.getApiUrl(`users/${this.employee.id}`), updateData, {
      headers: this.getAuthToken() ? { Authorization: `Bearer ${this.getAuthToken()}` } : {}
    }).subscribe({
      next: (response: any) => {
        // If there's a temporary image file, upload it
        if (this.tempImageFile) {
          this.uploadProfileImageFile(this.tempImageFile);
        } else {
          // No image to upload, just finish the save process
          this.finalizeSave();
        }
      },
      error: (error: any) => {
        console.error('Failed to update user data:', error);
        this.isLoading = false;
      }
    });
  }
  
  private finalizeSave(): void {
    // Update original employee data
    this.originalEmployee = { ...this.employee };
    this.originalImageUrl = this.employee.profile_image_url || '';
    
    // Update user state service
    this.userStateService.updateUser(this.employee);
    
    // Clear temporary image data
    this.tempImageFile = null;
    this.tempImageUrl = '';
    
    // Exit edit mode
    this.isEditing = false;
    this.isLoading = false;
  }
  
  /**
   * Handle file input change event
   */
  handleFileInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      const file = input.files[0];
      
      // Store the file temporarily
      this.tempImageFile = file;
      
      // Create a temporary URL for preview
      const reader = new FileReader();
      reader.onload = (e) => {
        this.tempImageUrl = e.target?.result as string;
        // Update the employee object for immediate preview
        this.employee.profile_image_url = this.tempImageUrl;
      };
      reader.readAsDataURL(file);
    }
  }
  
  /**
   * Upload profile image to the server
   */
  private uploadProfileImageFile(file: File): void {
    const formData = new FormData();
    formData.append('file', file);
    
    const uploadUrl = this.getApiUrl(`files/upload-profile-image/${this.employee.id}`);
    
    this.http.post(uploadUrl, formData, {
      headers: this.getAuthToken() ? { Authorization: `Bearer ${this.getAuthToken()}` } : {}
    }).subscribe({
      next: (response: any) => {
        // Update profile image URL in employee object
        if (response && response.profile_image_url) {
          const imageUrl = this.formatImageUrl(response.profile_image_url);
          this.employee.profile_image_url = imageUrl;
          
          // Update user state service
          this.userStateService.updateUserProfileImage(imageUrl);
        }
        
        this.finalizeSave();
      },
      error: (error: any) => {
        console.error('Failed to upload profile image:', error);
        this.isLoading = false;
      }
    });
  }
  
  /**
   * Getter for profile image source with fallback
   */
  get profileImageSrc(): string {
    return this.userStateService.getProfileImageSrc(this.employee);
  }
  
  /**
   * Handle image loading error by setting a default image
   */
  handleImageError(event: Event): void {
    const imgElement = event.target as HTMLImageElement;
    imgElement.src = this.userStateService.getProfileImageSrc();
  }
  
  /**
   * Trigger the file input click event
   */
  triggerFileInput(): void {
    this.fileInput.nativeElement.click();
  }
  
  /**
   * Handle the uploaded event from the file uploader component (legacy)
   */
  handleUploadedEvent(event: FileUploaderEvent): void {
    // This method is kept for backward compatibility but not used in the new flow
    console.log('Legacy upload event:', event);
  }
}