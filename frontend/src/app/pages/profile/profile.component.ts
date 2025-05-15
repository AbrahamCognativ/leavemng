import {Component, OnInit, ViewChild, ElementRef} from '@angular/core';
import {DxFormModule} from 'devextreme-angular/ui/form';
import {DxButtonModule} from 'devextreme-angular/ui/button';
import {DxFileUploaderModule} from 'devextreme-angular/ui/file-uploader';
import {DxTextBoxModule} from 'devextreme-angular/ui/text-box';
import {CommonModule} from '@angular/common';
import {HttpClient, HttpClientModule, HttpHeaders} from '@angular/common/http';
import { environment } from '../../../environments/environment';

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

export class ProfileComponent implements OnInit {
  employee: Employee = {} as Employee;
  colCountByScreen: object;
  isEditing: boolean = false;
  originalEmployee: Employee = {} as Employee;
  baseUrl: string = environment.apiUrl; // Hardcoded API URL instead of using environment
  basePlainUrl: string = environment.apiBaseUrl
  isLoading: boolean = false;
  uploadUrl: string = '';
  @ViewChild('fileInput') fileInput!: ElementRef;
  
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
  
  constructor(private http: HttpClient) {
    this.colCountByScreen = {
      xs: 1,
      sm: 2,
      md: 3,
      lg: 4
    };
  }
  
  ngOnInit(): void {
    try {
      // First get basic user info from local storage
      const rawUser = localStorage.getItem("current_user");
      const parsedUser = rawUser ? JSON.parse(rawUser) : null;

      if (parsedUser && parsedUser.id) {
        // Initialize with data from local storage
        this.employee = {
          id: parsedUser.id,
          name: parsedUser.name || '',
          email: parsedUser.email || '',
          passport_or_id_number: parsedUser.passport_or_id_number || '',
          manager_id: parsedUser.manager_id || null,
          role_band: parsedUser.role_band || '',
          role_title: parsedUser.role_title || '',
          gender: parsedUser.gender || '',
          profile_image_url: parsedUser.profile_image_url || '',
          org_unit_id: parsedUser.org_unit_id || null,
          extra_metadata: parsedUser.extra_metadata || {},
          token: parsedUser.token || ''
        };
        
        this.uploadUrl = this.getApiUrl(`files/upload-profile-image/${parsedUser.id}`);
        
        // Then fetch the latest user data from the API
        this.refreshUserData();
      } else {
        console.error('No user ID found in local storage');
      }
    } catch (err) {
      console.error('Failed to load user data:', err);
    }
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
    
    // Validate passwords match
    if (this.passwordData.newPassword !== this.passwordData.confirmPassword) {
      this.passwordErrorMessage = 'Passwords do not match';
      return;
    }
    
    // Validate password complexity
    if (!this.passwordPattern.test(this.passwordData.newPassword)) {
      this.passwordErrorMessage = 'Password must include at least one uppercase letter, one lowercase letter, one number, and one special character';
      return;
    }
    
    this.isChangingPassword = true;
    
    // Get token from localStorage
    const token = localStorage.getItem('user_token') || '';
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });
    
    // Since there's no dedicated password change endpoint, we'll use the update user endpoint
    // with the password field. In a production app, this should be a dedicated endpoint with proper validation.
    const payload = {
      password: this.passwordData.newPassword
    };
    
    // Call API to update user with new password
    this.http.put(this.getApiUrl(`users/${this.employee.id}`), payload, { headers })
      .subscribe({
        next: () => {
          this.isChangingPassword = false;
          this.passwordSuccessMessage = 'Password changed successfully';
          
          // Reset form
          this.passwordData = {
            currentPassword: '',
            newPassword: '',
            confirmPassword: ''
          };
        },
        error: (error) => {
          this.isChangingPassword = false;
          this.passwordErrorMessage = error.error?.detail || 'Failed to change password. Please try again.';
          console.error('Error changing password:', error);
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
    
    // If it's a relative path, prepend the base URL
    if (url.startsWith('/uploads')) {
      return `${this.basePlainUrl}${url}`;
    }
    
    // Otherwise, assume it's a relative path without leading slash
    return `${this.baseUrl}/${url}`;
  }
  
  /**
   * Refresh user data from the API
   */
  refreshUserData(): void {
    this.isLoading = true;
    
    this.http.get(this.getApiUrl(`users/${this.employee.id}`))
      .subscribe({
        next: (userData: any) => {
          // Update employee object with fresh data from API
          const updatedEmployee = {
            ...this.employee,
            ...userData,
            // Ensure ID is preserved exactly as it was
            id: this.employee.id
          };
          
          // Fix profile image URL if needed
          if (updatedEmployee.profile_image_url) {
            updatedEmployee.profile_image_url = this.formatImageUrl(updatedEmployee.profile_image_url);
          }
          
          this.employee = updatedEmployee;
          
          // Update local storage with fresh data
          localStorage.setItem('current_user', JSON.stringify(this.employee));
          
          // Store original state for comparison when editing
          this.originalEmployee = {...this.employee};
          this.isLoading = false;
        },
        error: (error: any) => {
          console.error('Failed to fetch user data from API:', error);
          // Still use what we have from local storage
          this.originalEmployee = {...this.employee};
          this.isLoading = false;
        }
      });
  }
  
  /**
   * Toggle edit mode on/off
   */
  toggleEdit(): void {
    if (this.isEditing) {
      // If we're currently editing, this is a cancel action
      this.employee = {...this.originalEmployee};
    }
    this.isEditing = !this.isEditing;
  }
  
  /**
   * Save changes to the user profile
   */
  saveChanges(): void {
    this.isLoading = true;
    
    // Create update object with only changed fields
    const updateData: any = {};
    for (const key in this.employee) {
      // Skip email, role_band, role_title, and gender as they cannot be updated
      if (key === 'email' || key === 'role_band' || key === 'role_title' || key === 'gender') continue;
      
      // Only include fields that have changed
      if (this.employee[key] !== this.originalEmployee[key]) {
        updateData[key] = this.employee[key];
      }
    }
    
    // Only make API call if there are changes
    if (Object.keys(updateData).length > 0) {
      this.http.put(this.getApiUrl(`users/${this.employee.id}`), updateData)
        .subscribe({
          next: (response: any) => {
            // Update local storage with new user data
            const currentUser = JSON.parse(localStorage.getItem('current_user') || '{}');
            const updatedUser = {...currentUser, ...updateData};
            localStorage.setItem('current_user', JSON.stringify(updatedUser));
            
            // Update original employee data
            this.originalEmployee = {...this.employee};
            this.isLoading = false;
            this.isEditing = false;
            
            // Refresh the page to show updated data
            this.refreshUserData();
          },
          error: (error: any) => {
            console.error('Failed to update profile:', error);
            this.isLoading = false;
          }
        });
    } else {
      // No changes to save
      this.isLoading = false;
      this.isEditing = false;
    }
  }
  
  /**
   * Handle file input change event
   */
  handleFileInput(event: Event): void {
    const target = event.target as HTMLInputElement;
    const files = target.files;
    if (files && files.length > 0) {
      this.uploadProfileImage(files[0]);
    }
  }
  
  /**
   * Upload profile image to the server
   */
  uploadProfileImage(file: File): void {
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    // Get auth token if available
    const rawUser = localStorage.getItem("current_user");
    const parsedUser = rawUser ? JSON.parse(rawUser) : null;
    const token = parsedUser?.token || '';
    
    this.isLoading = true;
    // Ensure we have the correct URL with user ID
    const uploadUrl = this.getApiUrl(`files/upload-profile-image/${this.employee.id}`);
    
    this.http.post(uploadUrl, formData, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    }).subscribe({
      next: (response: any) => {
        // Update profile image URL in employee object
        if (response && response.profile_image_url) {
          // Format the image URL consistently
          const imageUrl = this.formatImageUrl(response.profile_image_url);
          
          this.employee.profile_image_url = imageUrl;
          this.originalEmployee.profile_image_url = imageUrl;
          
          // Update local storage
          const currentUser = JSON.parse(localStorage.getItem('current_user') || '{}');
          currentUser.profile_image_url = imageUrl;
          localStorage.setItem('current_user', JSON.stringify(currentUser));
          
          // Force refresh the image by creating a new URL with timestamp
          setTimeout(() => {
            const refreshedUrl = imageUrl + '?t=' + new Date().getTime();
            this.employee.profile_image_url = refreshedUrl;
          }, 500);
        }
        
        this.isLoading = false;
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
    // First try to use the profile_image_url
    if (this.employee?.profile_image_url) {
      return this.employee.profile_image_url;
    }
    
    // Then try to use avatarUrl as fallback
    if (this.employee?.avatarUrl) {
      return this.employee.avatarUrl;
    }
    
    // Use gender-specific default avatars if gender is available
    if (this.employee?.gender === 'Male') {
      return 'https://cdn-icons-png.flaticon.com/512/847/847969.png';
    } else if (this.employee?.gender === 'Female') {
      return 'https://cdn-icons-png.flaticon.com/512/4140/4140047.png';
    }
    
    // Default fallback
    return 'https://cdn-icons-png.flaticon.com/512/847/847969.png';
  }
  
  /**
   * Handle image loading error by setting a default image
   */
  handleImageError(event: Event): void {
    const imgElement = event.target as HTMLImageElement;
    imgElement.src = "https://cdn-icons-png.flaticon.com/512/847/847969.png";
  }
  
  /**
   * Trigger the file input click event
   */
  triggerFileInput(): void {
    this.fileInput.nativeElement.click();
  }
  
  /**
   * Handle the uploaded event from the file uploader component
   */
  handleUploadedEvent(event: FileUploaderEvent): void {
    if (event && event.request && event.request.response) {
      try {
        const response = JSON.parse(event.request.response);
        
        if (response && response.profile_image_url) {
          // Format the image URL consistently
          const imageUrl = this.formatImageUrl(response.profile_image_url);
          
          this.employee.profile_image_url = imageUrl;
          this.originalEmployee.profile_image_url = imageUrl;
          
          // Update local storage
          const currentUser = JSON.parse(localStorage.getItem('current_user') || '{}');
          currentUser.profile_image_url = imageUrl;
          localStorage.setItem('current_user', JSON.stringify(currentUser));
          
          // Force refresh the image by creating a new URL with timestamp
          setTimeout(() => {
            const refreshedUrl = imageUrl + '?t=' + new Date().getTime();
            this.employee.profile_image_url = refreshedUrl;
          }, 500);
        }
      } catch (error) {
        console.error('Error parsing upload response:', error);
      } finally {
        this.isLoading = false;
      }
    }
  }
}
