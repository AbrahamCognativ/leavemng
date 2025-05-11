import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { LeaveService } from '../../../shared/services/leave.service';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxScrollViewModule } from 'devextreme-angular/ui/scroll-view';
import { DxFormModule } from 'devextreme-angular/ui/form';
import { DxiItemModule } from 'devextreme-angular/ui/nested';
import { UserService } from '../../../shared/services/user.service';
import { AuthService } from '../../../shared/services/auth.service';

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
  leaveRequestLeaveType: any = null;
  isLeaveRequestOwner: boolean = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private leaveService: LeaveService,
    private userService: UserService,
    private authService: AuthService
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
      // Capitalize user name
      this.leaveRequest.user_name = this.capitalize(
        (await this.userService.getUserById(this.leaveRequest.user_id))?.name || ''
      );

      // Compute total_days = end_date - start_date + 1
      const start = new Date(this.leaveRequest.start_date);
      const end = new Date(this.leaveRequest.end_date);
      const msPerDay = 1000 * 60 * 60 * 24;

      const diffDays = Math.round((end.getTime() - start.getTime()) / msPerDay) + 1;
      this.leaveRequest.duration = diffDays;

      // Fetch leave type info
      this.leaveRequestLeaveType = (
        await this.leaveService.getLeaveTypes()
      ).find(type => type.id === this.leaveRequest.leave_type_id);

      // Load documents
      this.documents = await this.leaveService.getLeaveDocuments(this.requestId);

      // Fetch decided_by info
      this.leaveRequest.decided_by = this.leaveRequest.decided_by ? this.capitalize((
        await this.userService.getUserById(this.leaveRequest.decided_by)
      )?.name || '') : null;

      // Format decided_at
      this.leaveRequest.decision_at = this.leaveRequest.decision_at ? new Date(this.leaveRequest.decision_at).toLocaleString() : null;

      // Check if the user is the owner of the leave request
      this.isLeaveRequestOwner = this.leaveRequest.user_id === (await this.authService.getUser()).data?.id;
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
      const existing = await this.leaveService.getLeaveRequestDetails(this.requestId);

      // Create a new object without id
      const { id, ...payloadWithoutId } = existing;

      const payload = {
        leave_type_id: existing.leave_type_id,
        start_date: existing.start_date,
        end_date: existing.end_date,
        id: existing.id,
        applied_at: existing.applied_at,
        user_id: existing.user_id,
        total_days: existing.total_days,
        comments: existing.comments,
        status: 'rejected',
        decision_at: new Date().toISOString(),
        decided_by: (await this.authService.getUser()).data?.id,
      };

      await this.leaveService.updateLeaveRequest(this.requestId, payload);
      await this.loadRequestDetails();
      this.router.navigate(['/admin/leave-requests']);
    } catch (error) {
      console.error('Error rejecting leave request:', error);
      // Log more details about the error

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

  capitalize(str: string): string {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }
}
