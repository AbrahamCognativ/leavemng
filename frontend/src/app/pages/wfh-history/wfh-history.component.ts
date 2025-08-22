import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { DxDataGridModule, DxDataGridTypes } from 'devextreme-angular/ui/data-grid';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
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
  selector: 'app-wfh-history',
  standalone: true,
  imports: [
    CommonModule,
    HttpClientModule,
    DxDataGridModule,
    DxLoadIndicatorModule
  ],
  templateUrl: './wfh-history.component.html',
  styleUrl: './wfh-history.component.scss'
})
export class WfhHistoryComponent implements OnInit {
  wfhHistory: WFHRequest[] = [];
  isLoading: boolean = false;
  errorMessage: string = '';
  currentUser: any = null;
  baseUrl: string = environment.apiUrl;

  constructor(
    private wfhService: WFHService,
    private authService: AuthService,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    this.loadCurrentUser();
    this.fetchWFHHistory();
  }

  private async loadCurrentUser(): Promise<void> {
    try {
      const userResp = await this.authService.getUser();
      this.currentUser = userResp?.data;
    } catch (error) {
      this.errorMessage = 'User not found. Please log in again.';
    }
  }

  async fetchWFHHistory(): Promise<void> {
    if (!this.currentUser?.id) {
      await this.loadCurrentUser();
      if (!this.currentUser?.id) {
        this.errorMessage = 'User ID not found. Please log in again.';
        return;
      }
    }

    this.isLoading = true;
    this.errorMessage = '';

    try {
      const allRequests = await this.wfhService.getWFHRequests();
      
      const currentDate = new Date();
      
      // Filter for approved WFH requests that belong to the current user AND have end dates that have passed
      this.wfhHistory = allRequests.filter((request: WFHRequest) => {
        const isApprovedAndOwnedByUser = request.status === 'approved' && 
                                        request.user_id === this.currentUser.id;
        
        const endDate = new Date(request.end_date);
        const hasEndDatePassed = endDate < currentDate;
        
        return isApprovedAndOwnedByUser && hasEndDatePassed;
      });
      
      // Approver names are now included in the API response
      
    } catch (error) {
      this.errorMessage = 'Failed to load WFH history. Please try again later.';
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
  
  formatDate(dateString: string): string {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString();
  }
}