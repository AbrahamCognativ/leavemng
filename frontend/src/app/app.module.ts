import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';
import { DxDataGridModule, DxFormModule, DxDateBoxModule, DxCalendarModule, DxChartModule, DxPieChartModule, DxSelectBoxModule } from 'devextreme-angular';
import { AppComponent } from './app.component';
import { DxHttpModule } from 'devextreme-angular/http';
import { SideNavOuterToolbarModule, SingleCardModule } from './layouts';
import { FooterModule, ResetPasswordFormModule, ChangePasswordFormModule, LoginFormModule } from './shared/components';
import { AuthService, ScreenService, AppInfoService } from './shared/services';
import { UnauthenticatedContentModule } from './unauthenticated-content';
import { AppRoutingModule } from './app-routing.module';
import { LeaveCalendarComponent } from './leave-calendar/leave-calendar.component';
import {DxButtonModule} from 'devextreme-angular/ui/button';

@NgModule({
  declarations: [
    AppComponent,
    LeaveCalendarComponent,
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
    DxSelectBoxModule,
    DxHttpModule,
    SideNavOuterToolbarModule,
    SingleCardModule,
    FooterModule,
    ResetPasswordFormModule,
    ChangePasswordFormModule,
    LoginFormModule,
    UnauthenticatedContentModule,
    AppRoutingModule,
  ],
  providers: [
    AuthService,
    ScreenService,
    AppInfoService
  ],
  exports: [
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
