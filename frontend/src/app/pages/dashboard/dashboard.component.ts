import {Component, NgModule} from '@angular/core';
import {DxPieChartModule} from 'devextreme-angular';
import {DxiSeriesModule} from 'devextreme-angular/ui/nested';
import {LeaveService} from '../../shared/services/leave.service';
import {AuthService, NavigationService} from '../../shared/services';
import {CommonModule} from '@angular/common';
import {DxLoadIndicatorModule} from 'devextreme-angular/ui/load-indicator';
import {DxDataGridModule} from 'devextreme-angular/ui/data-grid';
import {DxPopupModule} from 'devextreme-angular/ui/popup';
import {Router} from '@angular/router';
import {EditLeaveModalComponent} from './edit-leave-modal/edit-leave-modal.component';

@Component({
  templateUrl: 'dashboard.component.html',
  styleUrls: [ './dashboard.component.scss' ],
  standalone: false,
})

export class DashboardComponent {
  leaveRequests: any[] = [];
  statistics: any;
  pendingLeaves: number = 0;
  approvedLeaves: number = 0;
  rejectedLeaves: number = 0;
  leaveTypes: any[] = [];
  leaveTypeCounts: any[] = [];
  leaveBalances: any[] = [];
  isLoading: boolean = false;
  isAdmin: boolean = false;
  remainingLeaveDays: number = 0;
  
  // Edit leave modal properties
  editModalVisible: boolean = false;
  selectedLeaveRequest: any = null;

  constructor(
    private leaveService: LeaveService,
    private authService: AuthService,
    private router: Router,
    private navigationService: NavigationService
  ) { }

  async ngOnInit(): Promise<void> {
    this.loadStatistics();
    this.checkUserRole();
    // Refresh navigation to show any new policies
    await this.navigationService.refreshNavigation();
  }

  private async checkUserRole() {
    const user = await this.authService.getUser();
    this.isAdmin = user?.data?.role_band === 'HR' || user?.data?.role_band === 'Admin';
  }

  customizeLeaveTypeText = (pointInfo: any) => {
    return `${pointInfo.pointName}`;
  };

  onRowClick(e: any) {
    if (e.rowType === 'data' && e.rowIndex >= 0) {
      // Navigate to the leave details page for all leave requests
      this.router.navigate(['/leave-request', e.data.id]);
    }
  }
  
  openEditModal(leaveRequest: any): void {
    this.selectedLeaveRequest = leaveRequest;
    this.editModalVisible = true;
  }
  
  closeEditModal(): void {
    this.editModalVisible = false;
    this.selectedLeaveRequest = null;
  }
  
  onLeaveUpdated(event: any): void {
    if (event.success) {
      // Reload statistics to reflect any changes
      this.loadStatistics();
    }
  }

  async loadStatistics(): Promise<void> {
    try {
      this.isLoading = true;

      const userResp = await this.authService.getUser();
      const currentUserId = userResp?.data?.id;
      const userGender = userResp?.data?.gender?.toLowerCase();
      if (!currentUserId) {
        console.error("Current user not found");
        return;
      }

      // Get all leave types first
      const types = await this.leaveService.getLeaveTypes();
      this.leaveTypes = types;

      // Get leave balance from API (sum of balance_days for the user)
      const userLeaveData = await this.leaveService.getUserLeave(currentUserId);
      let totalBalance = 0;
      if (userLeaveData && userLeaveData.leave_balance && Array.isArray(userLeaveData.leave_balance)) {
        totalBalance = userLeaveData.leave_balance.reduce((sum: number, bal: any) => {
          // Skip maternity/paternity leave if user is not eligible
          const leaveType = types.find(t => t.id === bal.leave_type_id);
          if (leaveType) {
            const code = leaveType.code.toLowerCase();
            if ((code === 'maternity' && userGender !== 'female') || 
                (code === 'paternity' && userGender !== 'male')) {
              return sum;
            }
          }
          return sum + (bal.balance_days || 0);
        }, 0);
      }
      const totalAllowableLeaveDays = totalBalance;

      // Get all leave requests for current user
      const allRequests = await this.leaveService.getLeaveRequests();
      const requests = allRequests.filter(r => r.user_id === currentUserId);
      this.leaveRequests = requests;
      
      const pendingAndApprovedRequests = requests.filter(r => r.status === 'pending' || r.status === 'approved');
      const totalUsedLeaveDays = pendingAndApprovedRequests.reduce((total, request) => {
        // Skip maternity/paternity leave if user is not eligible
        const leaveType = types.find(t => t.id === request.leave_type_id);
        if (leaveType) {
          const code = leaveType.code.toLowerCase();
          if ((code === 'maternity' && userGender !== 'female') || 
              (code === 'paternity' && userGender !== 'male')) {
            return total;
          }
        }
        return total + (request.total_days || 0);
      }, 0);
      this.remainingLeaveDays = totalAllowableLeaveDays;

      // Calculate leave statistics
      this.pendingLeaves = requests.filter(r => r.status === 'pending').length;
      this.approvedLeaves = requests.filter(r => r.status === 'approved').length;
      this.rejectedLeaves = requests.filter(r => r.status === 'rejected').length;

      // Calculate leave balances and distribution for display
      const leaveDistribution: { [key: string]: { used: number; remaining: number; isEligible: boolean } } = {};
      const currentYear = new Date().getFullYear();

      // Initialize leaveDistribution with actual remaining balances from userLeaveData and zero used days
      types.forEach(type => {
        const typeDescription = type.description; // Use description as key, consistent with original
        const typeCode = type.code.toLowerCase();
        const isEligible = !((typeCode === 'maternity' && userGender !== 'female') || 
                           (typeCode === 'paternity' && userGender !== 'male'));
        
        const balanceRecord = userLeaveData.leave_balance?.find((b: any) => b.leave_type === type.code);
        // Default to 0 remaining if no balance record exists for this leave type for the user
        const currentRemainingDays = balanceRecord ? (balanceRecord.balance_days || 0) : 0;

        leaveDistribution[typeDescription] = {
          used: 0, // Initialize used days to 0
          remaining: currentRemainingDays,
          isEligible: isEligible
        };
      });

      // Calculate 'Used Days' from APPROVED leave requests for the current year
      const approvedRequestsCurrentYear = requests.filter(request => {
        const requestStartDate = request.start_date ? new Date(request.start_date) : null;
        const requestYear = requestStartDate ? requestStartDate.getFullYear() : null;
        return request.status === 'approved' && requestYear === currentYear;
      });

      approvedRequestsCurrentYear.forEach(request => {
        const leaveTypeInfo = types.find(t => t.id === request.leave_type_id);
        if (leaveTypeInfo) {
          const typeDescription = leaveTypeInfo.description;
          // Ensure the leave type exists in our distribution map and the user is eligible
          if (leaveDistribution[typeDescription] && leaveDistribution[typeDescription].isEligible) {
            leaveDistribution[typeDescription].used += (request.total_days || 0);
          }
        }
      });

      // Prepare data for display (this.leaveTypeCounts)
      this.leaveTypeCounts = Object.entries(leaveDistribution).map(([typeDescription, data]) => {
        // 'totalEntitlement' is the sum of dynamically calculated 'used' and actual 'remaining'
        const totalEntitlement = data.used + data.remaining; 
        return {
          type: typeDescription,
          total: totalEntitlement, // This is the effective total entitlement for progress bar context
          used: data.used,
          remaining: data.remaining,
          percentageUsed: totalEntitlement > 0 ? (data.used / totalEntitlement) * 100 : 0,
          isEligible: data.isEligible
        };
      });

      // Calculate total leave balance
      this.leaveBalances = [{
        totalBalance: this.remainingLeaveDays,
        year: currentYear
      }];

      // Update leave requests with type descriptions
      for (const request of requests) {
        const leaveType = types.find(t => t.id === request.leave_type_id);
        request.leave_type_description = leaveType?.description || 'Unknown';
      }
      this.leaveRequests = requests;
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      this.isLoading = false;
    }
  }
}

@NgModule({
  imports: [
    DxPieChartModule,
    DxiSeriesModule,
    DxDataGridModule,
    DxLoadIndicatorModule,
    DxPopupModule,
    CommonModule,
    EditLeaveModalComponent
  ],
  providers: [AuthService, LeaveService],
  declarations: [ DashboardComponent ],
  exports: [ DashboardComponent ]
})
export class DashboardModule { }
