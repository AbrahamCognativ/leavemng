import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Routes } from '@angular/router';
import { DxDataGridModule } from 'devextreme-angular/ui/data-grid';
import { DxFormModule } from 'devextreme-angular/ui/form';
import { DxButtonModule } from 'devextreme-angular/ui/button';
import { DxLoadIndicatorModule } from 'devextreme-angular/ui/load-indicator';
import { DxPopupModule } from 'devextreme-angular/ui/popup';
import { DxiItemModule } from 'devextreme-angular/ui/nested';
import { AdminDashboardComponent } from './admin-dashboard/admin-dashboard.component';
import { LeaveApprovalComponent } from './leave-approval/leave-approval.component';
import { LeaveTypesComponent } from './leave-types/leave-types.component';
import { LeaveRequestDetailsComponent } from './leave-request-details/leave-request-details.component';
import { OrgUnitsComponent } from './org-units/org-units.component';

const routes: Routes = [
  {
    path: '',
    component: AdminDashboardComponent
  },
  {
    path: 'approvals',
    component: LeaveApprovalComponent
  },
  {
    path: 'approvals/:id',
    component: LeaveRequestDetailsComponent
  },
  {
    path: 'leave-types',
    component: LeaveTypesComponent
  },
  {
    path: 'org-units',
    component: OrgUnitsComponent
  }
];

@NgModule({
  imports: [
    CommonModule,
    RouterModule.forChild(routes),
    DxDataGridModule,
    DxFormModule,
    DxButtonModule,
    DxLoadIndicatorModule,
    DxPopupModule,
    DxiItemModule,
    AdminDashboardComponent,
    LeaveApprovalComponent,
    LeaveTypesComponent,
    LeaveRequestDetailsComponent,
    OrgUnitsComponent
  ]
})
export class AdminModule { } 