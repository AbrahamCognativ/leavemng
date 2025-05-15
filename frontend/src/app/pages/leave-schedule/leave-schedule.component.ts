import { Component, CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UserService } from '../../shared/services/user.service';
import { 
  DxSchedulerModule, 
  DxLoadIndicatorModule, 
  DxButtonModule,
  DxToolbarModule,
  DxTemplateModule,
  DxTooltipModule,
} from 'devextreme-angular';

import { LeaveService } from '../../shared/services/leave.service';
import { AuthService } from '../../shared/services';
import DataSource from "devextreme/data/data_source";

@Component({
  selector: 'app-leave-schedule',
  standalone: true,
  imports: [
    CommonModule,
    DxSchedulerModule,
    DxLoadIndicatorModule,
    DxButtonModule,
    DxToolbarModule,
    DxTemplateModule,
    DxTooltipModule
],
  providers: [AuthService],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  templateUrl: './leave-schedule.component.html',
  styleUrls: ['./leave-schedule.component.scss']
})

export class LeaveScheduleComponent {
  currentDate: Date = new Date();
  currentView: string = 'month';
  views: string[] = ['month'];
  loading = true;
  schedulerHeight = 800;

  dataSource: DataSource;

  constructor(
    private leaveService: LeaveService,
    private userService: UserService,
  ) {
    this.dataSource = new DataSource({
      load: async (loadOptions) => {
        try {
          const data = await this.leaveService.getAllApprovedLeaves();
          const enrichedData = await Promise.all(data.map(async d => {
            const userId = d['user_id'];
            const leaveTypeId = d['leave_type_id'];

            if (!userId || !leaveTypeId) {
              throw new Error('User ID or Leave Type ID is missing or invalid');
            }
            const user = await this.userService.getUserById(userId);
            const leaveType = await this.leaveService.getLeaveTypes();

            const color = this.getColorForUser(userId);

            console.log("this is d:", d)
            return {
              ...d,
              startDate: new Date(d['start_date']),
              endDate: new Date(d['end_date']),
              formattedStartDate: new Date(d['start_date']).toLocaleDateString('en-GB', {
                year: 'numeric',
                month: 'short',
                day: '2-digit',
              }),
              formattedEndDate: new Date(d['end_date']).toLocaleDateString('en-GB', {
                year: 'numeric',
                month: 'short',
                day: '2-digit',
              }),
              employeeName: user?.name || d.employee_name || 'Unknown',
              employeeEmail: user?.email || d.employee_email || 'Unknown',
              employeeID: d['employee_id'],
              leaveType: d['leave_type'],
              description: d['comments'],
              allDay: d['all_day'],
              displayMessage: `${user?.name || d.employee_name || 'Unknown'}'s ${d['leave_type'] || leaveType.find((lt: any) => lt.id === leaveTypeId)?.code || 'Unknown'} leave`,
              color,
            };
          }));
         
          return enrichedData;
        } catch (error) {
          console.error('Error loading leave requests:', error);
          return [];
        }
      },
    });
  }

  getColorForUser(userId: string): string {
    const colors = [
      '#4caf50',
      '#2196f3',
      '#f44336',
      '#9c27b0',
      '#ff9800',
      '#3f51b5',
      '#00bcd4',
      '#e91e63',
    ];
    
    const hash = [...userId].reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return colors[hash % colors.length];
  }
}

