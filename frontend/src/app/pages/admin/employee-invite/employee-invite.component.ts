import { Component, OnInit } from '@angular/core';
import { DxFormModule } from 'devextreme-angular/ui/form';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxSelectBoxModule } from 'devextreme-angular/ui/select-box';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxPopupModule } from 'devextreme-angular/ui/popup';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule, HttpHeaders } from '@angular/common/http';
import { AuthService } from '../../../shared/services';
import { UserService, IUser } from '../../../shared/services/user.service';

interface NewEmployee {
  name: string;
  email: string;
  password: string;
  role_band: string;
  role_title: string;
  passport_or_id_number: string;
  gender: string;
  manager_id?: string;
  org_unit_id?: string;
}

interface Manager {
  id: string;
  name: string;
}

interface OrgUnit {
  id: string;
  name: string;
}

@Component({
  selector: 'app-employee-invite',
  templateUrl: './employee-invite.component.html',
  styleUrls: ['./employee-invite.component.scss'],
  standalone: true,
  imports: [
    DxFormModule, 
    DxButtonModule, 
    DxSelectBoxModule, 
    DxLoadIndicatorModule,
    DxDataGridModule,
    DxPopupModule,
    CommonModule, 
    HttpClientModule
  ]
})
export class EmployeeInviteComponent implements OnInit {
  newEmployee: NewEmployee = {
    name: '',
    email: '',
    password: '',
    role_band: '',
    role_title: '',
    passport_or_id_number: '',
    gender: '',
  };

  managers: Manager[] = [];
  orgUnits: OrgUnit[] = [];
  roleBands: string[] = ['IC', 'Manager', 'HR', 'Admin'];
  genderOptions: string[] = ['male', 'female'];
  
  isLoading: boolean = false;
  loadingUsers: boolean = false;
  successMessage: string = '';
  errorMessage: string = '';
  
  allUsers: IUser[] = [];
  selectedUser: IUser | null = null;
  isEditMode: boolean = false;
  
  colCountByScreen: object;
  baseUrl: string = 'http://localhost:8000';
  apiVersion: string = 'v1';

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private userService: UserService
  ) {
    this.colCountByScreen = {
      xs: 1,
      sm: 2,
      md: 3,
      lg: 4
    };
  }

  ngOnInit(): void {
    this.fetchManagers();
    this.fetchOrgUnits();
    this.fetchAllUsers();
  }
  
  async fetchAllUsers(): Promise<void> {
    this.loadingUsers = true;
    try {
      // Get token from localStorage
      const token = localStorage.getItem('user_token') || '';
      const headers = new HttpHeaders({
        'Authorization': `Bearer ${token}`
      });
      
      // Fetch all users
      this.http.get<IUser[]>(this.getApiUrl('users'), { headers })
        .subscribe({
          next: (users) => {
            this.allUsers = users;
            this.loadingUsers = false;
          },
          error: (error) => {
            console.error('Error fetching users:', error);
            this.loadingUsers = false;
          }
        });
    } catch (error) {
      console.error('Error fetching users:', error);
      this.loadingUsers = false;
    }
  }

  getApiUrl(endpoint: string): string {
    return `${this.baseUrl}/api/${this.apiVersion}/${endpoint}`;
  }

  fetchManagers(): void {
    // Get token from localStorage instead of AuthService
    const token = localStorage.getItem('user_token') || '';
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });

    this.http.get<any[]>(this.getApiUrl('users'), { headers })
      .subscribe({
        next: (users) => {
          this.managers = users.map(user => ({
            id: user.id,
            name: user.name
          }));
        },
        error: (error) => {
          console.error('Error fetching managers:', error);
        }
      });
  }

  fetchOrgUnits(): void {
    // Get token from localStorage instead of AuthService
    const token = localStorage.getItem('user_token') || '';
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });

    // The correct endpoint for org units is 'org'
    this.http.get<any[]>(this.getApiUrl('org'), { headers })
      .subscribe({
        next: (orgUnits) => {
          this.orgUnits = orgUnits.map(unit => ({
            id: unit.id,
            name: unit.name
          }));
          console.log('Org units loaded:', this.orgUnits);
        },
        error: (error) => {
          console.error('Error fetching org units:', error);
        }
      });
  }

  // Generate a random password of specified length
  generateRandomPassword(length: number = 10): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*';
    let password = '';
    
    // Ensure at least one uppercase, one lowercase, one number, and one special character
    password += chars.charAt(Math.floor(Math.random() * 26)); // Uppercase
    password += chars.charAt(26 + Math.floor(Math.random() * 26)); // Lowercase
    password += chars.charAt(52 + Math.floor(Math.random() * 10)); // Number
    password += chars.charAt(62 + Math.floor(Math.random() * 8)); // Special
    
    // Fill the rest randomly
    for (let i = 4; i < length; i++) {
      password += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    
    // Shuffle the password
    return password.split('').sort(() => 0.5 - Math.random()).join('');
  }
  
  inviteEmployee(): void {
    this.isLoading = true;
    this.successMessage = '';
    this.errorMessage = '';

    // We don't need to generate a password as the backend will handle this
    // and send an invite email with instructions

    // Get token from localStorage instead of AuthService
    const token = localStorage.getItem('user_token') || '';
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });

    // Create the invite request payload (without password)
    const inviteRequest = {
      name: this.newEmployee.name,
      email: this.newEmployee.email,
      role_band: this.newEmployee.role_band,
      role_title: this.newEmployee.role_title,
      passport_or_id_number: this.newEmployee.passport_or_id_number,
      gender: this.newEmployee.gender,
      manager_id: this.newEmployee.manager_id,
      org_unit_id: this.newEmployee.org_unit_id
    };

    this.http.post(this.getApiUrl('auth/invite'), inviteRequest, { headers })
      .subscribe({
        next: (response: any) => {
          this.isLoading = false;
          this.successMessage = `User ${this.newEmployee.name} has been successfully invited. An email with instructions has been sent to ${this.newEmployee.email}.`;
          
          // Reset form
          this.newEmployee = {
            name: '',
            email: '',
            password: '',
            role_band: '',
            role_title: '',
            passport_or_id_number: '',
            gender: '',
          };
          
          // Refresh the user list
          this.fetchAllUsers();
        },
        error: (error) => {
          this.isLoading = false;
          this.errorMessage = error.error?.detail || 'Failed to invite user. Please try again.';
          console.error('Error inviting user:', error);
        }
      });
  }

  // Helper method for DevExtreme SelectBox
  displayManagerName(item: any): string {
    return item ? item.name : '';
  }

  // Helper method for DevExtreme SelectBox
  displayOrgUnitName(item: any): string {
    return item ? item.name : '';
  }
  
  formatDate(dateString: string): string {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString();
  }
  
  editUser(user: IUser): void {
    this.selectedUser = { ...user };
    this.isEditMode = true;
  }
  
  cancelEdit(): void {
    this.selectedUser = null;
    this.isEditMode = false;
  }
  
  saveUserChanges(): void {
    if (!this.selectedUser) return;
    
    this.isLoading = true;
    const token = localStorage.getItem('user_token') || '';
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });
    
    this.http.put(`${this.getApiUrl('users')}/${this.selectedUser.id}`, this.selectedUser, { headers })
      .subscribe({
        next: () => {
          this.isLoading = false;
          this.successMessage = `User ${this.selectedUser?.name} has been successfully updated.`;
          this.isEditMode = false;
          this.selectedUser = null;
          this.fetchAllUsers(); // Refresh the list
        },
        error: (error) => {
          this.isLoading = false;
          this.errorMessage = error.error?.detail || 'Failed to update user. Please try again.';
          console.error('Error updating user:', error);
        }
      });
  }
}
