import {Component, NgModule} from '@angular/core';
import {DxPieChartModule} from 'devextreme-angular';
import {DxiSeriesModule} from 'devextreme-angular/ui/nested';
import {LeaveService} from '../../shared/services/leave.service';
import {AuthService} from '../../shared/services';
import {CommonModule} from '@angular/common';
import {DxLoadIndicatorModule} from 'devextreme-angular/ui/load-indicator';
import {DxDataGridModule} from 'devextreme-angular/ui/data-grid';

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

  constructor(
    private leaveService: LeaveService,
    private authService: AuthService
  ) { }

  ngOnInit(): void {
    this.loadStatistics();
  }

  customizeLeaveTypeText = (pointInfo: { pointColor: string; pointIndex: number; pointName: any }): string => {
    return `${pointInfo.pointName}`;
  };

  async loadStatistics(): Promise<void> {
    try {
      this.isLoading = true;

      const userResp = await this.authService.getUser();
      console.log('userResp', userResp);
      const currentUserId = userResp?.data?.id;

      if (!currentUserId) {
        console.error("Current user not found");
        return;
      }

      const allRequests = await this.leaveService.getLeaveRequests();
      const requests = allRequests.filter(r => r.user_id === currentUserId);
      this.leaveRequests = requests;

      this.pendingLeaves = requests.filter(r => r.status === 'pending').length;
      this.approvedLeaves = requests.filter(r => r.status === 'approved').length;
      this.rejectedLeaves = requests.filter(r => r.status === 'rejected').length;

      const types = await this.leaveService.getLeaveTypes();
      this.leaveTypes = types;

      const typeCounts: { [key: string]: number } = {};
      for (const req of requests) {
        const typeName = req.leave_type?.description || 'Unknown';
        typeCounts[typeName] = (typeCounts[typeName] || 0) + 1;
      }

      this.leaveTypeCounts = Object.entries(typeCounts).map(([type, count]) => ({
        type,
        count
      }));

      // Optional: Only fetch balances if needed for the same user
      const balances = requests; // or await service if balances are different
      this.leaveBalances = balances;

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
    CommonModule
  ],
  providers: [AuthService, LeaveService],
  declarations: [ DashboardComponent ],
  exports: [ DashboardComponent ]
})
export class DashboardModule { }
