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

// PMS Base Styles
import colors from "assets/theme-dark/base/colors";

const { info, dark } = colors;

const globals = {
  html: {
    scrollBehavior: "smooth",
  },
  "*, *::before, *::after": {
    margin: 0,
    padding: 0,
  },
  "a, a:link, a:visited": {
    textDecoration: "none !important",
  },
  "a.link, .link, a.link:link, .link:link, a.link:visited, .link:visited": {
    color: `${dark.main} !important`,
    transition: "color 150ms ease-in !important",
  },
  "a.link:hover, .link:hover, a.link:focus, .link:focus": {
    color: `${info.main} !important`,
  },
  "&.Mui-disabled":{
    color:"white !important",
    "-webkit-text-fill-color":"white !important"
  },
  "&.MuiPickersPopper-paper":{
    backgroundColor:"#202940 !important"
  },
  "&.rs-picker-daterange .rs-input-group-addon .rs-btn-close":{
    color:"white"
  },
  "&.rs-picker-popup .rs-calendar .rs-calendar-time-dropdown-column>ul,.rs-picker-popup .rs-calendar ,.rs-picker-daterange-header,.rs-calendar-time-dropdown-column-title,.rs-calendar-time-view .rs-calendar-time-dropdown,.rs-picker-popup .rs-picker-toolbar,.rs-calendar-header-meridian":{
    backgroundColor:"#202940",
    color:"white"
  }

};

export default globals;
