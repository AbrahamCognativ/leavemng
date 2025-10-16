import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import {HTTP_INTERCEPTORS, HttpClientModule, provideHttpClient} from '@angular/common/http';
import { DxDataGridModule, DxFormModule, DxDateBoxModule, DxCalendarModule, DxChartModule, DxPieChartModule, DxSelectBoxModule, DxLoadIndicatorModule, DxPopupModule, DxButtonModule } from 'devextreme-angular';
import { AppComponent } from './app.component';
import { DxHttpModule } from 'devextreme-angular/http';
import { SideNavOuterToolbarModule, SingleCardModule } from './layouts';
import { FooterModule, ResetPasswordFormModule, ChangePasswordFormModule, LoginFormModule } from './shared/components';
import { AuthService, ScreenService, AppInfoService } from './shared/services';
import { OrgUnitService } from './shared/services/org-unit.service';
import { UnauthenticatedContentModule } from './unauthenticated-content';
import { AppRoutingModule } from './app-routing.module';
import { LeaveCalendarComponent } from './leave-calendar/leave-calendar.component';
import {UserService} from './shared/services/user.service';
import {LeaveService} from './shared/services/leave.service';
import { UserStateService } from './shared/services/user-state.service';
import { NextOfKinService } from './shared/services/next-of-kin.service';
import {DxiItemModule, DxiSeriesModule} from 'devextreme-angular/ui/nested';
import {DashboardModule} from './pages/dashboard/dashboard.component';
import {AuthInterceptor} from './shared/services/authinceptor.service';
import { configureDevExtreme } from './shared/config/devextreme.config';
import { DocsComponent } from './pages/docs/docs.component';
import { NextOfKinReminderModalComponent } from './shared/components/next-of-kin-reminder-modal/next-of-kin-reminder-modal.component';

// Configure DevExtreme license
configureDevExtreme();

@NgModule({
  declarations: [
    AppComponent,
    LeaveCalendarComponent,
    NextOfKinReminderModalComponent,
  ],
  imports: [
    BrowserModule,
    HttpClientModule,
    DxDataGridModule,
    DxDateBoxModule,
    DxCalendarModule,
    DxButtonModule,
    DxFormModule,
    DxChartModule,
    DxPieChartModule,
    DxiSeriesModule,
    DxSelectBoxModule,
    DxPopupModule,
    DxHttpModule,
    SideNavOuterToolbarModule,
    SingleCardModule,
    FooterModule,
    ResetPasswordFormModule,
    ChangePasswordFormModule,
    LoginFormModule,
    DashboardModule,
    UnauthenticatedContentModule,
    AppRoutingModule,
    DxLoadIndicatorModule,
    DxiItemModule,
    DocsComponent
  ],
  providers: [
    {provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true},
    AuthService,
    ScreenService,
    AppInfoService,
    UserService,
    LeaveService, 
    OrgUnitService,
    UserStateService,
    NextOfKinService
  ],
  exports: [
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }