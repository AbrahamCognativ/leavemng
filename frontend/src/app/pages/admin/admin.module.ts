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
import { LeaveTypesComponent } from './leave-types/leave-types.component';
import { LeaveRequestDetailsComponent } from './leave-request-details/leave-request-details.component';
import { OrgUnitsComponent } from './org-units/org-units.component';
import { EmployeeInviteComponent } from './employee-invite/employee-invite.component';
import { AuditLogsComponent } from './audit-logs/audit-logs.component';
import { LeavesComponent } from './leaves/leaves.component';
import { AuthService } from '../../shared/services';
import { Router, CanActivate } from '@angular/router';
import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class AdminGuard implements CanActivate {
  constructor(private authService: AuthService, private router: Router) {}

  canActivate(): boolean {
    if (!this.authService.isAdmin && !this.authService.isHR && !this.authService.isManager) {
      this.router.navigate(['/dashboard']);
      return false;
    }
    return true;
  }
}

const routes: Routes = [
  {
    path: '',
    redirectTo: 'leaves',
    pathMatch: 'full'
  },
  {
    path: 'leaves',
    component: LeavesComponent,
    canActivate: [AdminGuard]
  },
  {
    path: 'leave-requests',
    component: AdminDashboardComponent,
    canActivate: [AdminGuard]
  },
  {
    path: 'leave-request/:id',
    component: LeaveRequestDetailsComponent,
    canActivate: [AdminGuard]
  },
  {
    path: 'leave-types',
    component: LeaveTypesComponent,
    canActivate: [AdminGuard]
  },
  {
    path: 'org-units',
    component: OrgUnitsComponent,
    canActivate: [AdminGuard]
  },
  {
    path: 'employee-invite',
    component: EmployeeInviteComponent,
    canActivate: [AdminGuard]
  },
  {
    path: 'audit-logs',
    component: AuditLogsComponent,
    canActivate: [AdminGuard]
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
    LeaveTypesComponent,
    LeaveRequestDetailsComponent,
    OrgUnitsComponent,
    EmployeeInviteComponent,
    AuditLogsComponent
  ],
  providers: [AdminGuard]
})
export class AdminModule { }
