import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxDateBoxModule } from 'devextreme-angular/ui/date-box';
import { DxSelectBoxModule } from 'devextreme-angular/ui/select-box';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxTextBoxModule } from 'devextreme-angular/ui/text-box';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxPopupModule } from 'devextreme-angular/ui/popup';
import { AuthService } from '../../../shared/services';
import notify from 'devextreme/ui/notify';

interface AuditLog {
  id: string;
  user_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  timestamp: string | null;
  extra_metadata?: any;
  user_name?: string;
  user_email?: string;
  resource_name?: string;
  resource_details?: any;
}

interface AuditLogResponse {
  data: AuditLog[];
  total: number;
  skip: number;
  limit: number;
}

@Component({
  selector: 'app-audit-logs',
  templateUrl: './audit-logs.component.html',
  styleUrls: ['./audit-logs.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    HttpClientModule,
    DxDataGridModule,
    DxDateBoxModule,
    DxSelectBoxModule,
    DxButtonModule,
    DxTextBoxModule,
    DxLoadIndicatorModule,
    DxPopupModule
  ]
})
export class AuditLogsComponent implements OnInit {
  auditLogs: AuditLog[] = [];
  isLoading = false;
  totalCount = 0;
  currentPage = 0;
  pageSize = 20;
  
  // Filter options
  resourceTypes: string[] = [];
  actions: string[] = [];
  selectedResourceType: string | null = null;
  selectedAction: string | null = null;
  fromDate: Date = new Date(0); // Use epoch time as default empty date
  toDate: Date = new Date(0); // Use epoch time as default empty date
  hasFromDateFilter = false;
  hasToDateFilter = false;
  
  // Detail view
  selectedLog: AuditLog | null = null;
  isDetailPopupVisible = false;
  
  constructor(private http: HttpClient, private authService: AuthService) { }

  ngOnInit(): void {
    this.loadAuditLogs();
  }

  loadAuditLogs() {
    this.isLoading = true;
    
    // Prepare query parameters
    const params: any = {
      skip: this.currentPage * this.pageSize,
      limit: this.pageSize
      // We're using a custom sorting in the backend that prioritizes non-null timestamps
      // and sorts them in descending order, so we don't need to specify sort and order here
    };
    
    if (this.selectedResourceType) {
      params.resource_type = this.selectedResourceType;
    }
    
    if (this.selectedAction) {
      params.action = this.selectedAction;
    }
    
    // User ID filter - uncomment when implemented
    // if (this.selectedUserId) {
    //   params.user_id = this.selectedUserId;
    // }
    
    if (this.hasFromDateFilter) {
      params.from_date = this.fromDate.toISOString();
    }
    
    if (this.hasToDateFilter) {
      params.to_date = this.toDate.toISOString();
    }
    
    // Make API request
    this.http.get<AuditLogResponse>(`${environment.apiUrl}/audit-logs`, { params })
      .subscribe({
        next: (response) => {
          this.auditLogs = response.data;
          this.totalCount = response.total;
          this.isLoading = false;
          
          // Extract unique resource types and actions for filters
          this.extractFilterOptions();
        },
        error: (error) => {
          console.error('Error loading audit logs:', error);
          this.isLoading = false;
          notify('Failed to load audit logs', 'error', 3000);
          
          // If API fails, show a message to the user
          this.auditLogs = [];
          this.totalCount = 0;
        }
      });
  }
  
  extractFilterOptions(): void {
    // Extract unique resource types
    const resourceTypesSet = new Set<string>();
    const actionsSet = new Set<string>();
    
    this.auditLogs.forEach(log => {
      if (log.resource_type) {
        resourceTypesSet.add(log.resource_type);
      }
      if (log.action) {
        actionsSet.add(log.action);
      }
    });
    
    this.resourceTypes = Array.from(resourceTypesSet);
    this.actions = Array.from(actionsSet);
  }
  
  onPageChanged(e: any): void {
    this.currentPage = e.page;
    this.pageSize = e.pageSize;
    this.loadAuditLogs();
  }
  
  applyFilters(): void {
    this.currentPage = 0; // Reset to first page
    this.loadAuditLogs();
  }
  
  resetFilters(): void {
    this.selectedResourceType = null;
    this.selectedAction = null;
    this.fromDate = new Date(0);
    this.toDate = new Date(0);
    this.hasFromDateFilter = false;
    this.hasToDateFilter = false;
    this.currentPage = 0;
    this.loadAuditLogs();
  }
  
  onFromDateChanged(e: any): void {
    if (e.value) {
      this.fromDate = e.value;
      this.hasFromDateFilter = true;
    } else {
      this.hasFromDateFilter = false;
    }
  }

  onToDateChanged(e: any): void {
    if (e.value) {
      this.toDate = e.value;
      this.hasToDateFilter = true;
    } else {
      this.hasToDateFilter = false;
    }
  }

  viewDetails(log: AuditLog): void {
    this.selectedLog = log;
    this.isDetailPopupVisible = true;
  }
  
  closeDetailPopup(): void {
    this.isDetailPopupVisible = false;
    this.selectedLog = null;
  }
  
  formatTimestamp(timestamp: string | null): string {
    if (!timestamp) return 'N/A';
    try {
      return new Date(timestamp).toLocaleString();
    } catch (error) {
      console.error('Error formatting timestamp:', error);
      return 'Invalid Date';
    }
  }
  
  formatJson(json: any): string {
    if (!json) return '';
    return JSON.stringify(json, null, 2);
  }
}
