import { useEffect } from "react";

// react-router-dom components
import { useLocation } from "react-router-dom";

// prop-types is a library for typechecking of props.
import PropTypes from "prop-types";

// PMS components
import MDBox from "components/MDBox";

// PMS context
import { useMaterialUIController, setLayout } from "context";

function CustomerDashboardLayout({ children }) {
  const [controller, dispatch] = useMaterialUIController();
  const { miniSidenav } = controller;
  const { pathname } = useLocation();

  useEffect(() => {
    setLayout(dispatch, "customerDashboard");
  }, [dispatch, pathname]);

  return (
    <MDBox maxWidth={{ sm: "400px" }} margin={{ sm: "0px auto" }}>
      {children}
    </MDBox>
  );
}

// Typechecking props for the CustomerDashboardLayout
CustomerDashboardLayout.propTypes = {
  children: PropTypes.node.isRequired,
};

export default CustomerDashboardLayout;
