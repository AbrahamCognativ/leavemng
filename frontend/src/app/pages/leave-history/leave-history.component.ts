import { Component, OnInit } from '@angular/core';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';

interface LeaveRequest {
  id: string;
  user_id: string;
  leave_type_id: string;
  start_date: string;
  end_date: string;
  total_days: number;
  status: string;
  applied_at: string;
  decided_at?: string; // API field name
  decision_at?: string; // Database field name
  decided_by?: string;
  comments?: string;
  leave_type?: string; // We'll populate this from the leave type ID
  approver_name?: string; // We'll populate this from the decided_by ID
  [key: string]: any;
}

interface User {
  id: string;
  name: string;
  email: string;
  role_band: string;
  role_title: string;
  [key: string]: any;
}

interface LeaveType {
  id: string;
  code: string;
  description?: string;
  default_allocation_days?: number;
  custom_code?: string;
  [key: string]: any;
}

@Component({
  selector: 'app-leave-history',
  standalone: true,
  imports: [
    CommonModule,
    HttpClientModule,
    DxDataGridModule,
    DxButtonModule,
    DxLoadIndicatorModule
  ],
  templateUrl: './leave-history.component.html',
  styleUrl: './leave-history.component.scss'
})
export class LeaveHistoryComponent implements OnInit {
  leaveHistory: LeaveRequest[] = [];
  leaveTypes: LeaveType[] = [];
  users: Map<string, User> = new Map(); // Cache for user details
  isLoading: boolean = false;
  errorMessage: string = '';
  baseUrl: string = 'http://localhost:8000';
  apiVersion: string = 'v1';
  currentUser: any = null;
  leaveTypeMap: Map<string, string> = new Map();

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadCurrentUser();
    // First fetch leave types, then fetch leave history
    this.fetchLeaveTypes();
  }

  loadCurrentUser(): void {
    const rawUser = localStorage.getItem('current_user');
    if (rawUser) {
      this.currentUser = JSON.parse(rawUser);
    } else {
      this.errorMessage = 'User not found. Please log in again.';
    }
  }
  
  fetchLeaveTypes(): void {
    // Get auth token
    const token = this.currentUser?.token || '';
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    this.http.get(this.getApiUrl('leave-types'), { headers })
      .subscribe({
        next: (types: any) => {
          this.leaveTypes = types;
          
          // Create a map of leave type IDs to codes for easy lookup
          this.leaveTypes.forEach(type => {
            this.leaveTypeMap.set(type.id, type.code);
          });
          
          // Now fetch leave history after leave types are loaded
          this.fetchLeaveHistory();
        },
        error: (error) => {
          console.error('Error fetching leave types:', error);
          // Still try to fetch leave history even if leave types fail
          this.fetchLeaveHistory();
        }
      });
  }

  getApiUrl(endpoint: string): string {
    // Remove leading slash if present
    if (endpoint.startsWith('/')) {
      endpoint = endpoint.substring(1);
    }
    // Ensure trailing slash
    if (!endpoint.endsWith('/') && endpoint.length > 0) {
      endpoint = `${endpoint}/`;
    }
    return `${this.baseUrl}/api/${this.apiVersion}/${endpoint}`;
  }

  fetchLeaveHistory(): void {
    if (!this.currentUser || !this.currentUser.id) {
      this.errorMessage = 'User ID not found. Please log in again.';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    // Get the current date
    const currentDate = new Date().toISOString().split('T')[0];
    
    // Get auth token
    const token = this.currentUser?.token || '';
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Get all leave requests - the API already filters by current user
    this.http.get(this.getApiUrl('leave'), { headers })
      .subscribe({
        next: (leaveRequests: any) => {
          if (!leaveRequests || leaveRequests.length === 0) {
            this.leaveHistory = [];
            this.isLoading = false;
            return;
          }
          
          // Filter for all approved leaves that belong to the current user
          this.leaveHistory = leaveRequests.filter((leave: LeaveRequest) => {
            return leave.status === 'approved' && 
                   leave.user_id === this.currentUser.id;
          });
          
          console.log('All leave requests:', leaveRequests);
          console.log('Current user ID:', this.currentUser.id);
          
          // Log raw response to debug field names
          console.log('Raw leave requests:', JSON.stringify(leaveRequests));
          
          // Enhance leave requests with leave type names and fix field name mismatch
          this.leaveHistory.forEach(leave => {
            // Map leave type ID to name
            leave.leave_type = this.leaveTypeMap.get(leave.leave_type_id) || 'Unknown';
            
            // IMPORTANT: The database has decision_at but the API schema maps it to decided_at
            // We need to check the raw response to see what's actually coming back
            if (leave.status === 'approved') {
              // Check if we have raw access to the database field
              if (leave.hasOwnProperty('decision_at') && leave.decision_at) {
                console.log(`Found decision_at field for leave ${leave.id}: ${leave.decision_at}`);
                // Map it to the field the template is expecting
                leave.decided_at = leave.decision_at;
              } else if (!leave.decided_at) {
                console.warn(`Leave ${leave.id} is approved but has no approval date. This is a data consistency issue.`);
              }
            }
          });
          
          // Fetch user details for approvers
          this.fetchApproverDetails();
          
          console.log('Filtered leave history:', this.leaveHistory);
          this.isLoading = false;
        },
        error: (error) => {
          console.error('Error fetching leave requests:', error);
          this.errorMessage = 'Failed to load leave history. Please check your authentication or try again later.';
          this.isLoading = false;
        }
      });
  }

  fetchApproverDetails(): void {
    // Get auth token
    const token = this.currentUser?.token || '';
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    // Get unique approver IDs
    const approverIds = new Set<string>();
    this.leaveHistory.forEach(leave => {
      if (leave.decided_by && !this.users.has(leave.decided_by)) {
        approverIds.add(leave.decided_by);
      }
    });
    
    if (approverIds.size === 0) {
      return; // No approvers to fetch
    }
    
    // Fetch user details for each approver
    approverIds.forEach(userId => {
      this.http.get(this.getApiUrl(`users/${userId}`), { headers })
        .subscribe({
          next: (user: any) => {
            this.users.set(userId, user);
            
            // Update leave requests with approver names
            this.leaveHistory.forEach(leave => {
              if (leave.decided_by === userId) {
                leave.approver_name = user.name || 'Unknown';
              }
            });
          },
          error: (error) => {
            console.error(`Error fetching user details for ID ${userId}:`, error);
          }
        });
    });
  }
  
  formatDate(dateString: string): string {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString();
  }

  refreshData(): void {
    this.fetchLeaveHistory();
  }
}
