import { Component } from '@angular/core';
import {DxPieChartModule} from 'devextreme-angular';
import {DxiSeriesModule} from 'devextreme-angular/ui/nested';
import {LeaveService} from '../../leave.service';

@Component({
  templateUrl: 'dashboard.component.html',
  styleUrls: [ './dashboard.component.scss' ],
  standalone: true,
  imports: [ DxPieChartModule, DxiSeriesModule]
})

export class DashboardComponent {
  statistics: any;
  pendingLeaves: number = 0;
  approvedLeaves: number = 0;
  rejectedLeaves: number = 0;
  leaveTypes: string[] = [];
  leaveTypeCounts: number[] = [];

  constructor(private leaveService: LeaveService) { }

  ngOnInit(): void {
    this.loadStatistics();
  }

  customizeLeaveTypeText = (pointInfo: { pointColor: string; pointIndex: number; pointName: any }): string => {
    return `${pointInfo.pointName}`;
  };

  loadStatistics(): void {
    this.leaveService.getLeaveStatistics().subscribe({
      next: (stats) => {
        this.statistics = stats;
        this.pendingLeaves = stats.pendingLeaves;
        this.approvedLeaves = stats.approvedLeaves;
        this.rejectedLeaves = stats.rejectedLeaves;

        // For leave type distribution chart
        this.leaveTypes = Object.keys(stats.leaveTypeDistribution);
        this.leaveTypeCounts = Object.values(stats.leaveTypeDistribution);
      },
      error: (err) => {
        console.error('Error loading statistics:', err);
      }
    });
  }
}
