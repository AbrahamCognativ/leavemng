import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LeaveService } from '../../../shared/services/leave.service';
import { AuthService } from '../../../shared/services';
import { UserService } from '../../../shared/services/user.service';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxTemplateModule } from 'devextreme-angular/core';
import { Router } from '@angular/router';

@Component({
  selector: 'app-leaves',
  templateUrl: './leaves.component.html',
  styleUrls: ['./leaves.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    DxDataGridModule,
    DxLoadIndicatorModule,
    DxTemplateModule
  ]
})
export class LeavesComponent implements OnInit {
  leaveRequests: any[] = [];
  isLoading: boolean = false;

  constructor(
    private leaveService: LeaveService,
    private authService: AuthService,
    private userService: UserService,
    private router: Router
  ) { }

  ngOnInit(): void {
    this.loadLeaveRequests();
  }

  async loadLeaveRequests(): Promise<void> {
    try {
      this.isLoading = true;
      const allRequests = await this.leaveService.getLeaveRequests();
      const leaveTypes = await this.leaveService.getLeaveTypes();
      
      // Filter for pending requests only
      const pendingRequests = allRequests.filter(r => r.status === 'pending');
      
      // Enrich leave requests with employee names and leave type descriptions
      for (const request of pendingRequests) {
        const leaveType = leaveTypes.find(t => t.id === request.leave_type_id);
        request.leave_type_description = leaveType?.description || 'Unknown';
        const user = await this.userService.getUserById(request.user_id);
        request.employee_name = user?.name || 'Unknown';
      }
      
      this.leaveRequests = pendingRequests;
    } catch (error) {
      console.error('Error loading leave requests:', error);
    } finally {
      this.isLoading = false;
    }
  }



  async approveLeave(leaveId: string): Promise<void> {
    try {
      this.isLoading = true;
      await this.leaveService.approveLeaveRequest(leaveId);
      // Reload the leave requests after approval
      await this.loadLeaveRequests();
    } catch (error) {
      console.error('Error approving leave:', error);
    } finally {
      this.isLoading = false;
    }
  }

  viewDetails(e: any): void {
    if (e.rowType === 'data') {
      this.router.navigate(['/admin/leave-request', e.data.id], {
        queryParams: { returnUrl: '/admin/leaves' }
      });
    }
  }
}
