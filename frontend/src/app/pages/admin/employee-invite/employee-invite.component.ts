import { Component, OnInit } from '@angular/core';
import { DxFormModule } from 'devextreme-angular/ui/form';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxSelectBoxModule } from 'devextreme-angular/ui/select-box';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxPopupModule } from 'devextreme-angular/ui/popup';
import { DxNumberBoxModule } from 'devextreme-angular/ui/number-box';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule, HttpHeaders } from '@angular/common/http';
import { AuthService } from '../../../shared/services';
import { UserService, IUser } from '../../../shared/services/user.service';
import { LeaveService } from '../../../shared/services/leave.service';
import { environment } from '../../../../environments/environment';

interface NewEmployee {
  name: string;
  email: string;
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
    DxNumberBoxModule,
    CommonModule, 
    HttpClientModule
  ]
})
export class EmployeeInviteComponent implements OnInit {
  newEmployee: NewEmployee = {
    name: '',
    email: '',
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
  isDeleteConfirmVisible: boolean = false;
  userToDelete: IUser | null = null;
  
  // Leave balance properties
  userLeaveBalances: any[] = [];
  leaveTypes: any[] = [];
  loadingLeaveData: boolean = false;
  isEditingLeaveBalance: boolean = false;
  selectedLeaveBalance: any = null;
  editedBalance: number = 0;
  
  colCountByScreen: object;
  baseUrl: string = environment.apiUrl;

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private userService: UserService,
    private leaveService: LeaveService
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
      // Get current user
      const userResponse = await this.authService.getUser();
      if (!userResponse?.data) {
        throw new Error('No current user found');
      }
      const currentUser = userResponse.data;
      // Get token from localStorage
      const token = localStorage.getItem('user_token') || '';
      const headers = new HttpHeaders({
        'Authorization': `Bearer ${token}`
      });
      
      // Fetch all users
      this.http.get<IUser[]>(this.getApiUrl('users'), { headers })
        .subscribe({
          next: (users) => {
            // Filter out the current user and the scheduler user from the list
            this.allUsers = users.filter(user => 
              user.id !== currentUser.id && 
              user.email.toLowerCase() !== 'scheduler@cognativ.com'
            );
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
    return `${this.baseUrl}/${endpoint}`;
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
          // Filter users to only include Admin, HR, or Manager roles
          const managerUsers = users.filter(user =>
            user.role_band === 'Admin' ||
            user.role_band === 'HR' ||
            user.role_band === 'Manager'
          );
          
          this.managers = managerUsers.map(user => ({
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
    
    // Fetch leave balances and types when editing a user
    this.fetchUserLeaveBalances(user.id);
    this.fetchLeaveTypes();
  }
  
  cancelEdit(): void {
    this.selectedUser = null;
    this.isEditMode = false;
    this.userLeaveBalances = [];
    this.isEditingLeaveBalance = false;
    this.selectedLeaveBalance = null;
  }
  
  saveUserChanges(): void {
    if (!this.selectedUser) return;
    
    this.isLoading = true;
    const token = localStorage.getItem('user_token') || '';
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });
    
    // Only include fields that are allowed to be updated
    const updateData = {
      name: this.selectedUser.name,
      passport_or_id_number: this.selectedUser.passport_or_id_number,
      gender: this.selectedUser.gender,
      manager_id: this.selectedUser.manager_id,
      org_unit_id: this.selectedUser.org_unit_id,
      is_active: this.selectedUser.is_active,
      role_band: this.selectedUser.role_band,
      role_title: this.selectedUser.role_title
    };
    
    this.http.patch(`${this.getApiUrl('users')}/${this.selectedUser.id}`, updateData, { headers })
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

  // Confirm delete
  confirmDelete(user: IUser): void {
    this.userToDelete = user;
    this.isDeleteConfirmVisible = true;
  }

  // Cancel delete
  cancelDelete(): void {
    this.isDeleteConfirmVisible = false;
    this.userToDelete = null;
  }

  // Deactivate user by setting is_active to false
  softDeleteUser(): void {
    if (!this.userToDelete) return;
    
    this.isLoading = true;
    const token = localStorage.getItem('user_token') || '';
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });
    
    // Use PATCH to update the user's is_active status
    const updateData = {
      is_active: false
    };
    
    this.http.patch(`${this.getApiUrl('users')}/${this.userToDelete.id}`, updateData, { headers })
      .subscribe({
        next: () => {
          this.isLoading = false;
          this.successMessage = `User ${this.userToDelete?.name} has been successfully deactivated.`;
          this.isDeleteConfirmVisible = false;
          this.userToDelete = null;
          this.fetchAllUsers(); // Refresh the list
        },
        error: (error) => {
          this.isLoading = false;
          this.errorMessage = error.error?.detail || 'Failed to deactivate user. Please try again.';
          console.error('Error deactivating user:', error);
        }
      });
  }
  
  // Fetch leave balances for a specific user
  async fetchUserLeaveBalances(userId: string): Promise<void> {
    if (!userId) return;
    
    this.loadingLeaveData = true;
    try {
      const userData = await this.leaveService.getUserLeave(userId);
      if (userData && userData.leave_balance) {
        // Map the leave_balance array to include leave_type_name
        this.userLeaveBalances = userData.leave_balance.map((balance: any) => {
          // Find the matching leave type to get its name
          const leaveType = this.leaveTypes.find(type => type.code === balance.leave_type);
          return {
            ...balance,
            leave_type_id: leaveType?.id || '',
            leave_type_name: leaveType?.name || balance.leave_type,
            updated_at: new Date().toISOString() // The API doesn't return updated_at, so we use current date
          };
        });
      } else {
        this.userLeaveBalances = [];
      }
    } catch (error) {
      console.error('Error fetching user leave balances:', error);
      this.errorMessage = 'Failed to load leave balances. Please try again.';
      this.userLeaveBalances = [];
    } finally {
      this.loadingLeaveData = false;
    }
  }
  
  // Fetch all leave types
  async fetchLeaveTypes(): Promise<void> {
    try {
      this.leaveTypes = await this.leaveService.getLeaveTypes();
    } catch (error) {
      console.error('Error fetching leave types:', error);
      this.errorMessage = 'Failed to load leave types. Please try again.';
      this.leaveTypes = [];
    }
  }
  
  // Open leave balance edit popup
  editLeaveBalance(leaveBalance: any): void {
    this.selectedLeaveBalance = { ...leaveBalance };
    this.editedBalance = leaveBalance.balance_days;
    this.isEditingLeaveBalance = true;
    
    // Check if leave type ID exists
    if (!this.selectedLeaveBalance.leave_type_id && this.leaveTypes.length > 0) {
      const matchingLeaveType = this.leaveTypes.find(type => 
        type.code === this.selectedLeaveBalance.leave_type ||
        type.name === this.selectedLeaveBalance.leave_type_name
      );
      
      if (matchingLeaveType) {
        this.selectedLeaveBalance.leave_type_id = matchingLeaveType.id;
      } else {
      }
    }
  }
  
  // Cancel leave balance edit
  cancelLeaveBalanceEdit(): void {
    this.selectedLeaveBalance = null;
    this.isEditingLeaveBalance = false;
  }
  
  // Save leave balance changes
  async saveLeaveBalanceChanges(): Promise<void> {
    if (!this.selectedLeaveBalance || !this.selectedUser) {
      console.error('Missing required data:', { selectedLeaveBalance: this.selectedLeaveBalance, selectedUser: this.selectedUser });
      return;
    }
    
    this.isLoading = true;
    const token = localStorage.getItem('user_token') || '';
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });
    
    const updateData = {
      balance_days: this.editedBalance
    };
    
    
    try {
      // Find the leave type ID based on the leave type code
      let leaveTypeId = this.selectedLeaveBalance.leave_type_id;
      
      // If we don't have a leave type ID, try to find it from the leave types
      if (!leaveTypeId && this.leaveTypes.length > 0) {
        const leaveType = this.leaveTypes.find(type => 
          type.code === this.selectedLeaveBalance.leave_type ||
          type.name === this.selectedLeaveBalance.leave_type_name
        );
        if (leaveType) {
          leaveTypeId = leaveType.id;
        } else {
          console.error('Could not find matching leave type:', {
            leaveTypes: this.leaveTypes,
            searchCriteria: {
              code: this.selectedLeaveBalance.leave_type,
              name: this.selectedLeaveBalance.leave_type_name
            }
          });
          throw new Error('Could not determine leave type ID for update');
        }
      }
      
      const url = `${this.baseUrl}/leave/balance/${this.selectedUser.id}/${leaveTypeId}`;
      
      // Call the new endpoint to update leave balance
      const response = await this.http.put(
        url,
        updateData,
        { headers }
      ).toPromise();
      
      
      // Success handling
      this.isLoading = false;
      this.successMessage = `Leave balance for ${this.selectedLeaveBalance.leave_type_name} has been updated successfully.`;
      this.isEditingLeaveBalance = false;
      this.selectedLeaveBalance = null;
      
      // Refresh leave balances
      await this.fetchUserLeaveBalances(this.selectedUser.id);
    } catch (error: any) {
      this.isLoading = false;
      this.errorMessage = error.error?.detail || 'Failed to update leave balance. Please try again.';
    }
  }
}
