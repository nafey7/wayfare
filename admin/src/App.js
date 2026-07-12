import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useDispatch } from "react-redux";
import CssBaseline from "@mui/material/CssBaseline";
import { ThemeProvider } from "@mui/material/styles";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterMoment } from "@mui/x-date-pickers/AdapterMoment";
import Configurator from "examples/Configurator";
import Sidenav from "examples/Sidenav/index";
import "swiper/css";
import "swiper/css/bundle";
import "rsuite/dist/rsuite-no-reset.min.css";
import theme from "assets/theme";
import "assets/styles/utility.css";
import "assets/styles/index.css";
import themeDark from "assets/theme-dark";
import privateRoutes, { additionalRoutes } from "privateRoutes";
import routes from "routes";
import { setMiniSidenav, useMaterialUIController } from "context";
import { getSession } from "services/service";
import SignIn from "layouts/authentication/sign-in";

import { getMeInfo } from "store/slice/users/userSlice";
import { isEmpty } from "lodash";

export default function App() {
  const [controller] = useMaterialUIController();
  const {
    miniSidenav,
    direction,
    layout,
    sidenavColor,
    darkMode,
  } = controller;
  const [onMouseEnter, setOnMouseEnter] = useState(false);
  const { pathname } = useLocation();
  const { Authorization } = getSession();
  const devBypass = process.env.NODE_ENV === 'development' ? 'dev-token' : null; // Temporary bypass
  const isAuthenticated = Authorization || devBypass;
  const dispatch = useDispatch();

  useEffect(() => {
    if (!isEmpty(Authorization)) {
      dispatch(getMeInfo());
    }
  }, [dispatch, Authorization]);

  useEffect(() => {
    document.body.setAttribute("dir", direction);
    document.documentElement.scrollTop = 0;
    document.scrollingElement.scrollTop = 0;
  }, [direction, pathname]);

  const handleMouseEvents = (enter) => {
    if (miniSidenav && enter !== onMouseEnter) {
      setMiniSidenav(dispatch, !enter);
      setOnMouseEnter(enter);
    }
  };

  const displaySidenav = layout === "dashboard";
  return (
    <ThemeProvider theme={darkMode ? themeDark : theme}>
      <CssBaseline />
      <LocalizationProvider dateAdapter={AdapterMoment}>
        {displaySidenav && (
          <Sidenav
            color={sidenavColor}
            // brand={brandImage}
            brandName=""
            routes={isAuthenticated ? privateRoutes : routes}
            onMouseEnter={() => handleMouseEvents(true)}
            onMouseLeave={() => handleMouseEvents(false)}
          />
        )}
        <Configurator />
        <Routes>
          {isAuthenticated && (
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
          )}

          <Route path="/" element={<SignIn />} />

          {isAuthenticated &&
            privateRoutes.map((route) => (
              <Route
                key={route.key}
                path={route.route}
                element={route.component}
              />
            ))}

          {isAuthenticated &&
            additionalRoutes.map((route, index) => (
              <Route
                key={`additional-${index}`}
                path={route.route}
                element={route.component}
              />
            ))}

          <Route
            path="*"
            element={
              <div className="text-center">
                <h1>404 - Page Not Found</h1>
              </div>
            }
          />
        </Routes>
      </LocalizationProvider>
    </ThemeProvider>
  );
}
