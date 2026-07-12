/**
  This file is used for controlling the global states of the components,
  you can customize the states for the different components here.
*/

import { createContext, useContext, useReducer, useMemo } from "react";

// prop-types is a library for typechecking of props
import PropTypes from "prop-types";

// PMS main context
const MaterialUI = createContext();

// Setting custom name for the context which is visible on react dev tools
MaterialUI.displayName = "MaterialUIContext";

// PMS reducer
function reducer(state, action) {
  switch (action.type) {
    case "MINI_SIDENAV": {
      return { ...state, miniSidenav: action.value };
    }
    case "TRANSPARENT_SIDENAV": {
      return { ...state, transparentSidenav: action.value };
    }
    case "WHITE_SIDENAV": {
      return { ...state, whiteSidenav: action.value };
    }
    case "SIDENAV_COLOR": {
      return { ...state, sidenavColor: action.value };
    }
    case "TRANSPARENT_NAVBAR": {
      return { ...state, transparentNavbar: action.value };
    }
    case "FIXED_NAVBAR": {
      return { ...state, fixedNavbar: action.value };
    }
    case "OPEN_CONFIGURATOR": {
      return { ...state, openConfigurator: action.value };
    }
    case "DIRECTION": {
      return { ...state, direction: action.value };
    }
    case "LAYOUT": {
      return { ...state, layout: action.value };
    }
    case "DARKMODE": {
      return { ...state, darkMode: action.value };
    }
    default: {
      throw new Error(`Unhandled action type: ${action.type}`);
    }
  }
}

// PMS context provider
function MaterialUIControllerProvider({ children }) {
  const miniSidenav = localStorage.getItem('miniSidenav');
  const transparentSidenav = localStorage.getItem('transparentSidenav');
  const whiteSidenav = localStorage.getItem('whiteSidenav');
  const sidenavColor = localStorage.getItem('sidenavColor');
  const transparentNavbar = localStorage.getItem('transparentNavbar');
  const fixedNavbar = localStorage.getItem('fixedNavbar');
  const openConfigurator = localStorage.getItem('openConfigurator');
  const direction = localStorage.getItem('direction');
  const layout = localStorage.getItem('layout');
  const darkMode = localStorage.getItem('darkMode');

  const initialState = {
    miniSidenav: miniSidenav ? miniSidenav : false,
    transparentSidenav: transparentSidenav === "true" ? true : false,
    whiteSidenav: whiteSidenav === "true" ? true : false,
    sidenavColor: sidenavColor ? sidenavColor : "info",
    transparentNavbar: transparentNavbar === "true" ? true : false,
    fixedNavbar: fixedNavbar === "false" ? false : true,
    openConfigurator: openConfigurator === "true" ? true : false,
    direction: direction ? direction : "ltr",
    layout: layout ? layout : "dashboard",
    darkMode: darkMode === "true" ? true : false,
  };

  const [controller, dispatch] = useReducer(reducer, initialState);

  const value = useMemo(() => [controller, dispatch], [controller, dispatch]);

  return <MaterialUI.Provider value={value}>{children}</MaterialUI.Provider>;
}

// PMS custom hook for using context
function useMaterialUIController() {
  const context = useContext(MaterialUI);

  if (!context) {
    throw new Error(
      "useMaterialUIController should be used inside the MaterialUIControllerProvider."
    );
  }

  return context;
}

// Typechecking props for the MaterialUIControllerProvider
MaterialUIControllerProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

// Context module functions
const setMiniSidenav = (dispatch, value) => {
  dispatch({ type: "MINI_SIDENAV", value })
  localStorage.setItem('miniSidenav', value);
};
const setTransparentSidenav = (dispatch, value) => {
  dispatch({ type: "TRANSPARENT_SIDENAV", value })
  localStorage.setItem('transparentSidenav', value);
};
const setWhiteSidenav = (dispatch, value) => {
  dispatch({ type: "WHITE_SIDENAV", value })
  localStorage.setItem('whiteSidenav', value);
};
const setSidenavColor = (dispatch, value) => {
  dispatch({ type: "SIDENAV_COLOR", value })
  localStorage.setItem('sidenavColor', value);
};
const setTransparentNavbar = (dispatch, value) => {
  dispatch({ type: "TRANSPARENT_NAVBAR", value })
  localStorage.setItem('transparentNavbar', value);
};
const setFixedNavbar = (dispatch, value) => {
  dispatch({ type: "FIXED_NAVBAR", value })
  localStorage.setItem('fixedNavbar', value);
};
const setOpenConfigurator = (dispatch, value) => {
  dispatch({ type: "OPEN_CONFIGURATOR", value })
  localStorage.setItem('openConfigurator', value);
};
const setDirection = (dispatch, value) => {
  dispatch({ type: "DIRECTION", value })
  localStorage.setItem('direction', value);
};
const setLayout = (dispatch, value) => {
  dispatch({ type: "LAYOUT", value })
  localStorage.setItem('layout', value);
};
const setDarkMode = (dispatch, value) => {
  dispatch({ type: "DARKMODE", value })
  localStorage.setItem('darkMode', value);
};

export {
  MaterialUIControllerProvider,
  useMaterialUIController,
  setMiniSidenav,
  setTransparentSidenav,
  setWhiteSidenav,
  setSidenavColor,
  setTransparentNavbar,
  setFixedNavbar,
  setOpenConfigurator,
  setDirection,
  setLayout,
  setDarkMode,
};
