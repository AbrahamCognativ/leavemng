import { NgModule, inject } from '@angular/core';
import { Routes, RouterModule, Router } from '@angular/router';
import { LoginFormComponent, ResetPasswordFormComponent, ChangePasswordFormComponent } from './shared/components';
import { AuthGuardService, AuthService } from './shared/services';
import { ProfileComponent } from './pages/profile/profile.component';
import {DashboardComponent} from './pages/dashboard/dashboard.component';
import {LeaveRequestComponent} from './pages/leave-request/leave-request.component';
import {LeaveHistoryComponent} from './pages/leave-history/leave-history.component';
import {LeaveRequestDetailsComponent} from './pages/admin/leave-request-details/leave-request-details.component';
import {LeaveScheduleComponent} from './pages/leave-schedule/leave-schedule.component';
import {OrgChartComponent} from './pages/org-chart/org-chart.component';
import {SimpleOrgChartComponent} from './pages/org-chart/simple-org-chart.component';

const routes: Routes = [
  {
    path: 'profile',
    component: ProfileComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'leave/apply',
    component: LeaveRequestComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'leave/history',
    component: LeaveHistoryComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'leave/schedule',
    component: LeaveScheduleComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'leave-request/:id',
    component: LeaveRequestDetailsComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'dashboard',
    component: DashboardComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'org-chart',
    component: OrgChartComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'org-structure',
    component: SimpleOrgChartComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'admin',
    loadChildren: () => import('./pages/admin/admin.module').then(m => m.AdminModule),
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'login-form',
    component: LoginFormComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'reset-password',
    component: ResetPasswordFormComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'change-password/:token',
    component: ChangePasswordFormComponent
  },
  {
    path: '**',
    redirectTo: 'dashboard'
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes, {useHash: true})],
  providers: [AuthGuardService],
  exports: [RouterModule],
  declarations: [
  ]
})
export class AppRoutingModule { }
