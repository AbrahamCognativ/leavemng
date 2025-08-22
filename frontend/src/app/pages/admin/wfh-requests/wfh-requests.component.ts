import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxToastModule } from 'devextreme-angular/ui/toast';
import { DxPopupModule } from 'devextreme-angular/ui/popup';
import { DxFormModule } from 'devextreme-angular/ui/form';
import { DxiItemModule, DxoLabelModule, DxiColumnModule } from 'devextreme-angular/ui/nested';
import { WFHService } from '../../../shared/services/wfh.service';
import { AuthService } from '../../../shared/services/auth.service';

@Component({
  selector: 'app-wfh-requests',
  templateUrl: './wfh-requests.component.html',
  styleUrls: ['./wfh-requests.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    DxDataGridModule,
    DxButtonModule,
    DxToastModule,
    DxPopupModule,
    DxFormModule,
    DxiItemModule,
    DxoLabelModule,
    DxiColumnModule
  ]
})
export class WFHRequestsComponent implements OnInit {
  wfhRequests: any[] = [];
  loading = false;
  toastVisible = false;
  toastMessage = '';
  toastType: 'success' | 'error' | 'info' | 'warning' = 'info';
  
  // Popup for request details
  detailsPopupVisible = false;
  selectedRequest: any = null;
  
  // Current user info
  currentUser: any = null;
  isAdmin = false;
  isHR = false;
  isManager = false;

  constructor(
    private wfhService: WFHService,
    private authService: AuthService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.loadCurrentUser();
    await this.loadWFHRequests();
  }

  async loadCurrentUser(): Promise<void> {
    try {
      const userResult = await this.authService.getUser();
      if (userResult.isOk && userResult.data) {
        this.currentUser = userResult.data;
        this.isAdmin = this.authService.isAdmin;
        this.isHR = this.authService.isHR;
        this.isManager = this.authService.isManager;
      }
    } catch (error) {
      // Error loading current user - handled silently in production
    }
  }

  async loadWFHRequests(): Promise<void> {
    this.loading = true;
    try {
      this.wfhRequests = await this.wfhService.getWFHRequests();
    } catch (error) {
      this.showToast('Error loading WFH requests', 'error');
    } finally {
      this.loading = false;
    }
  }

  showToast(message: string, type: 'success' | 'error' | 'info' | 'warning'): void {
    this.toastMessage = message;
    this.toastType = type;
    this.toastVisible = true;
  }

  getStatusColor(status: string): string {
    switch (status?.toLowerCase()) {
      case 'approved': return '#28a745';
      case 'rejected': return '#dc3545';
      case 'pending': return '#ffc107';
      case 'cancelled': return '#6c757d';
      default: return '#6c757d';
    }
  }

  getStatusIcon(status: string): string {
    switch (status?.toLowerCase()) {
      case 'approved': return 'check';
      case 'rejected': return 'close';
      case 'pending': return 'clock';
      case 'cancelled': return 'remove';
      default: return 'help';
    }
  }

  formatDate(date: string | Date): string {
    if (!date) return '';
    const d = new Date(date);
    return d.toLocaleDateString('en-GB');
  }

  calculateDays(startDate: string | Date, endDate: string | Date): number {
    if (!startDate || !endDate) return 0;
    
    const start = new Date(startDate);
    const end = new Date(endDate);
    let days = 0;
    const current = new Date(start);

    while (current <= end) {
      const day = current.getDay();
      if (day !== 0 && day !== 6) { // Skip weekends
        days++;
      }
      current.setDate(current.getDate() + 1);
    }

    return days;
  }

  canApproveReject(request: any): boolean {
    // Can't approve/reject own requests
    if (request.user_id === this.currentUser?.id) {
      return false;
    }
    
    // Only pending requests can be approved/rejected
    if (request.status?.toLowerCase() !== 'pending') {
      return false;
    }
    
    // Admin and HR can approve/reject all
    if (this.isAdmin || this.isHR) {
      return true;
    }
    
    // Managers can approve/reject their direct reports
    if (this.isManager) {
      // This would need to be enhanced to check if the request user reports to current user
      return true;
    }
    
    return false;
  }

  async approveRequest(request: any): Promise<void> {
    if (!this.canApproveReject(request)) {
      this.showToast('You do not have permission to approve this request', 'error');
      return;
    }

    try {
      await this.wfhService.approveWFHRequest(request.id);
      this.showToast('WFH request approved successfully', 'success');
      await this.loadWFHRequests();
    } catch (error: any) {
      let errorMessage = 'Error approving WFH request';
      if (error?.error?.detail) {
        errorMessage = error.error.detail;
      }
      this.showToast(errorMessage, 'error');
    }
  }

  async rejectRequest(request: any): Promise<void> {
    if (!this.canApproveReject(request)) {
      this.showToast('You do not have permission to reject this request', 'error');
      return;
    }

    try {
      await this.wfhService.rejectWFHRequest(request.id);
      this.showToast('WFH request rejected successfully', 'success');
      await this.loadWFHRequests();
    } catch (error: any) {
      let errorMessage = 'Error rejecting WFH request';
      if (error?.error?.detail) {
        errorMessage = error.error.detail;
      }
      this.showToast(errorMessage, 'error');
    }
  }

  viewDetails(request: any): void {
    this.selectedRequest = {
      ...request,
      working_days: this.calculateDays(request.start_date, request.end_date)
    };
    this.detailsPopupVisible = true;
  }

  closeDetailsPopup(): void {
    this.detailsPopupVisible = false;
    this.selectedRequest = null;
  }

  // Custom cell templates for the data grid
  statusCellTemplate = (cellData: any) => {
    const status = cellData.value?.toLowerCase() || 'unknown';
    return `
      <div style="display: flex; align-items: center; gap: 8px;">
        <i class="dx-icon-${this.getStatusIcon(status)}" style="color: ${this.getStatusColor(status)};"></i>
        <span style="color: ${this.getStatusColor(status)}; font-weight: 500; text-transform: capitalize;">
          ${cellData.value || 'Unknown'}
        </span>
      </div>
    `;
  }

  actionsCellTemplate = (cellData: any) => {
    const request = cellData.data;
    const canApprove = this.canApproveReject(request);
    
    return `
      <div style="display: flex; gap: 8px;">
        <button class="dx-button dx-button-mode-text" onclick="viewDetails('${request.id}')" title="View Details">
          <i class="dx-icon-info"></i>
        </button>
        ${canApprove ? `
          <button class="dx-button dx-button-mode-text" onclick="approveRequest('${request.id}')" title="Approve" style="color: #28a745;">
            <i class="dx-icon-check"></i>
          </button>
          <button class="dx-button dx-button-mode-text" onclick="rejectRequest('${request.id}')" title="Reject" style="color: #dc3545;">
            <i class="dx-icon-close"></i>
          </button>
        ` : ''}
      </div>
    `;
  }
}