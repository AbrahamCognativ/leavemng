import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { LeaveService } from '../../../shared/services/leave.service';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxScrollViewModule } from 'devextreme-angular/ui/scroll-view';
import { DxFormModule } from 'devextreme-angular/ui/form';
import { DxiItemModule } from 'devextreme-angular/ui/nested';

@Component({
  selector: 'app-leave-request-details',
  templateUrl: './leave-request-details.component.html',
  styleUrls: ['./leave-request-details.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    DxLoadIndicatorModule,
    DxButtonModule,
    DxScrollViewModule,
    DxFormModule,
    DxiItemModule
  ]
})
export class LeaveRequestDetailsComponent implements OnInit {
  requestId: string | null = null;
  leaveRequest: any = null;
  documents: any[] = [];
  isLoading: boolean = false;
  isApproving: boolean = false;
  isRejecting: boolean = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private leaveService: LeaveService
  ) { }

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.requestId = params['id'];
      if (this.requestId) {
        this.loadRequestDetails();
      }
    });
  }

  async loadRequestDetails(): Promise<void> {
    if (!this.requestId) return;

    try {
      this.isLoading = true;
      this.leaveRequest = await this.leaveService.getLeaveRequestDetails(this.requestId);
      this.documents = await this.leaveService.getLeaveDocuments(this.requestId);
    } catch (error) {
      console.error('Error loading leave request details:', error);
    } finally {
      this.isLoading = false;
    }
  }

  async approveRequest(): Promise<void> {
    if (!this.requestId) return;

    try {
      this.isApproving = true;
      await this.leaveService.approveLeaveRequest(this.requestId);
      await this.loadRequestDetails();
      this.router.navigate(['/admin/leave-requests']);
    } catch (error) {
      console.error('Error approving leave request:', error);
    } finally {
      this.isApproving = false;
    }
  }

  async rejectRequest(): Promise<void> {
    if (!this.requestId) return;

    try {
      this.isRejecting = true;
      await this.leaveService.updateLeaveRequest(this.requestId, { status: 'rejected' });
      await this.loadRequestDetails();
      this.router.navigate(['/admin/leave-requests']);
    } catch (error) {
      console.error('Error rejecting leave request:', error);
    } finally {
      this.isRejecting = false;
    }
  }

  async downloadDocument(documentId: string): Promise<void> {
    if (!this.requestId) return;

    try {
      const blob = await this.leaveService.downloadLeaveDocument(this.requestId, documentId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `document-${documentId}`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading document:', error);
    }
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'pending': return 'status-pending';
      case 'approved': return 'status-approved';
      case 'rejected': return 'status-rejected';
      default: return '';
    }
  }
} 