import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LeaveService } from '../../../shared/services/leave.service';
import { AuthService } from '../../../shared/services';
import { UserService } from '../../../shared/services/user.service';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxTextBoxModule } from 'devextreme-angular/ui/text-box';
import { Router } from '@angular/router';
import DataSource from 'devextreme/data/data_source';

@Component({
  selector: 'app-admin-dashboard',
  templateUrl: './admin-dashboard.component.html',
  styleUrls: ['./admin-dashboard.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    DxDataGridModule,
    DxLoadIndicatorModule,
    DxTextBoxModule
  ]
})
export class AdminDashboardComponent implements OnInit {
  leaveRequests: any[] = [];
  leaveTypes: any[] = [];
  statistics: any = {
    totalRequests: 0,
    pendingRequests: 0,
    approvedRequests: 0,
    rejectedRequests: 0
  };
  isLoading: boolean = false;
  searchText: string = '';
  dataSource: any;

  constructor(
    private leaveService: LeaveService,
    private authService: AuthService,
    private userService: UserService,
    private router: Router
  ) { }

  ngOnInit(): void {
    this.loadStatistics();
  }

  async loadStatistics(): Promise<void> {
    try {
      this.isLoading = true;
      const allRequests = await this.leaveService.getLeaveRequests();
      this.leaveRequests = allRequests;
      
      this.statistics = {
        totalRequests: allRequests.length,
        pendingRequests: allRequests.filter(r => r.status === 'pending').length,
        approvedRequests: allRequests.filter(r => r.status === 'approved').length,
        rejectedRequests: allRequests.filter(r => r.status === 'rejected').length
      };

      const types = await this.leaveService.getLeaveTypes();
      this.leaveTypes = types;
      for (const request of allRequests) {
        const leaveType = types.find(t => t.id === request.leave_type_id);
        request.leave_type_description = leaveType?.description || 'Unknown';
        request.employee_name = await this.userService.getUserById(request.user_id).then(user => user?.name);
      }
      
      // Initialize DataSource for advanced grid features
      this.setupDataSource();
    } catch (error) {
      console.error('Error loading admin dashboard data:', error);
    } finally {
      this.isLoading = false;
    }
  }

  setupDataSource(): void {
    this.dataSource = new DataSource({
      store: this.leaveRequests,
      searchExpr: ['employee_name', 'leave_type_description', 'status']
    });
  }

  onSearchChange(e: any): void {
    this.dataSource.searchValue(e.value);
    this.dataSource.load();
  }

  viewRequest(e: any): void {
    this.router.navigate(['/admin/leave-request', e.row.data.id], {
      queryParams: { returnUrl: '/admin/leave-requests' }
    });
  }

  onRowClick(e: any): void {
    if (e.rowType === 'data' && e.rowIndex >= 0) {
      // Don't navigate if they clicked on the button column
      if (e.column && e.column.type === 'buttons') {
        return;
      }
      this.router.navigate(['/admin/leave-request', e.data.id], {
        queryParams: { returnUrl: '/admin/leave-requests' }
      });
    }
  }
}
