/**
=========================================================
* PMS - v2.2.0
=========================================================

* Product Page: https://www.creative-tim.com/product/material-dashboard-react
* Copyright 2023 Creative Tim (https://www.creative-tim.com)

Coded by www.creative-tim.com

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

// PMS base styles
import breakpoints from "assets/theme-dark/base/breakpoints";

// PMS helper functions
import pxToRem from "assets/theme-dark/functions/pxToRem";

const {
  values: { sm, md, lg, xl, xxl },
} = breakpoints;

const SM = `@media (min-width: ${sm}px)`;
const MD = `@media (min-width: ${md}px)`;
const LG = `@media (min-width: ${lg}px)`;
const XL = `@media (min-width: ${xl}px)`;
const XXL = `@media (min-width: ${xxl}px)`;

const sharedClasses = {
  paddingRight: `${pxToRem(24)} !important`,
  paddingLeft: `${pxToRem(24)} !important`,
  marginRight: "auto !important",
  marginLeft: "auto !important",
  width: "100% !important",
  position: "relative",
};

const container = {
  [SM]: {
    ".MuiContainer-root": {
      ...sharedClasses,
      maxWidth: "540px !important",
    },
  },
  [MD]: {
    ".MuiContainer-root": {
      ...sharedClasses,
      maxWidth: "720px !important",
    },
  },
  [LG]: {
    ".MuiContainer-root": {
      ...sharedClasses,
      maxWidth: "960px !important",
    },
  },
  [XL]: {
    ".MuiContainer-root": {
      ...sharedClasses,
      maxWidth: "1140px !important",
    },
  },
  [XXL]: {
    ".MuiContainer-root": {
      ...sharedClasses,
      maxWidth: "1320px !important",
    },
  },
  //dark celendar//
  "&.css-xwhnvh.MainLayout-container": {
    backgroundColor: "#202940",
  },
  "&.css-xwhnvh .MainLayout-background": {
    backgroundColor: "#202940 !important",
  },
  "&.css-1vr53zw-MuiTableCell-root .Cell-dayOfMonth": {
    color: "white !important",
  },
  "&.css-15ys0s9-MuiTableCell-root.Cell-cell:only-child": {
    backgroundColor: "#202940",
  },
  "&.css-1vr53zw-MuiTableCell-root .Cell-dayOfWeek": {
    color: "white !important",
  },
  "&.css-1ya276g .Label-text": {
    color: "white !important",
  },
  "&.css-1chyqm4.Layout-flexRow ": {
    backgroundColor: "#202940",
  },
  "&.css-1vh0r5b-MuiToolbar-root.Toolbar-toolbar": {
    backgroundColor: "#202940",
  },
  "&.css-1hbvjip.DayScaleEmptyCell-emptyCell": {
    backgroundColor: "#202940",
  },
  //dark celendar//
  "&.css-v5vvaj-MuiContainer-root":{
    paddingLeft:"0px !important",
    paddingRight:"0px !important"
  },
  "&.css-1e2kxz0-MuiPickersCalendarHeader-labelContainer,.css-154cs8t-MuiPickersYear-root":{
    color:"white"
  },
  "&.css-1wy1au7-MuiTypography-root-MuiDayCalendar-weekDayLabel,.css-2xdetu-MuiButtonBase-root-MuiPickersDay-root":{
    color:"white !important"
  },
  "&.css-w3nzev-MuiButtonBase-root-MuiPickersDay-root:not(.Mui-selected)":{
    color:"white",
    border:"1px solid white !important"
  },
  "&.css-1c35hjw-MuiPaper-root-MuiAccordion-root":{
    backgroundColor:"#202940 !important"
  },
  "&.css-rffgq9-MuiTypography-root,.css-niqf4j-MuiStack-root>:not(style):not(style)":{
    color:"#ffffff !important"
  },
  "&.rs-picker-daterange>.rs-input-group.rs-input-group-inside .rs-input,.css-1xwgyfb-MuiSvgIcon-root":{
    color:"white"
  },
  "&.css-1xif2b4-MuiPopper-root-MuiDataGrid-menu .MuiDataGrid-menuList":{
    backgroundColor:"#1a2035"
  }

  };

export default container;
