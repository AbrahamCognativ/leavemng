import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { Router } from '@angular/router';
import { WFHService } from '../../shared/services/wfh.service';
import { AuthService } from '../../shared/services';
import { environment } from '../../../environments/environment';

interface WFHRequest {
  id: string;
  user_id: string;
  start_date: string;
  end_date: string;
  working_days: number;
  reason?: string;
  status: string;
  applied_at: string;
  decision_at?: string;
  decided_by?: string;
  approver_name?: string;
  [key: string]: any;
}

@Component({
  selector: 'app-wfh-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    HttpClientModule,
    DxDataGridModule,
    DxLoadIndicatorModule,
    DxButtonModule
  ],
  templateUrl: './wfh-dashboard.component.html',
  styleUrl: './wfh-dashboard.component.scss'
})
export class WfhDashboardComponent implements OnInit {
  wfhRequests: WFHRequest[] = [];
  pendingRequests: number = 0;
  approvedRequests: number = 0;
  rejectedRequests: number = 0;
  isLoading: boolean = false;
  currentUser: any = null;
  baseUrl: string = environment.apiUrl;

  constructor(
    private wfhService: WFHService,
    private authService: AuthService,
    private router: Router,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    this.loadCurrentUser();
    this.loadWFHRequests();
  }

  private async loadCurrentUser(): Promise<void> {
    try {
      const userResp = await this.authService.getUser();
      this.currentUser = userResp?.data;
    } catch (error) {
      // Error loading current user - handled silently in production
    }
  }

  async loadWFHRequests(): Promise<void> {
    if (!this.currentUser?.id) {
      // If user not loaded yet, try again
      await this.loadCurrentUser();
      if (!this.currentUser?.id) {
        return;
      }
    }

    try {
      this.isLoading = true;

      // Get all WFH requests for current user
      const allRequests = await this.wfhService.getWFHRequests();
      
      // Filter requests for current user
      this.wfhRequests = allRequests.filter((r: any) => r.user_id === this.currentUser.id);

      // Calculate statistics
      this.pendingRequests = this.wfhRequests.filter(r => r.status === 'pending').length;
      this.approvedRequests = this.wfhRequests.filter(r => r.status === 'approved').length;
      this.rejectedRequests = this.wfhRequests.filter(r => r.status === 'rejected').length;

      // Approver names are now included in the API response

    } catch (error) {
      // Error loading WFH requests - handled silently in production
    } finally {
      this.isLoading = false;
    }
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
    return `${this.baseUrl}/${endpoint}`;
  }

  onRowClick(e: any): void {
    if (e.rowType === 'data' && e.rowIndex >= 0) {
      // Navigate to WFH request details or edit page if needed
      // Row click functionality can be implemented here
    }
  }

  formatDate(dateString: string): string {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString();
  }

  getStatusClass(status: string): string {
    switch (status?.toLowerCase()) {
      case 'approved':
        return 'status-approved';
      case 'rejected':
        return 'status-rejected';
      case 'pending':
        return 'status-pending';
      default:
        return '';
    }
  }

  refreshData(): void {
    this.loadWFHRequests();
  }

  navigateToApply(): void {
    this.router.navigate(['/wfh/apply']);
  }
}