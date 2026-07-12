// @mui material components
import Card from "@mui/material/Card";
import Grid from "@mui/material/Grid";
// PMS components
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

// Data
import { useMaterialUIController } from "context";
import { useEffect, useState } from "react";
// import CreateUser from "./components/CreateUser";
import UserTable from "./components/UserTable";
import Footer from "examples/Footer";
import DashboardLayout from "examples/LayoutContainers/DashboardLayout";
import DashboardNavbar from "examples/Navbars/DashboardNavbar";
import { useDispatch, useSelector } from "react-redux";
import { isEmpty } from "lodash";
import { getUsers } from "store/slice/users/userSlice";
// import { getUsers } from "store/slice/users/userSlice";

function MyUsers() {
  const dispatch = useDispatch();
  const [controller] = useMaterialUIController();
  const { sidenavColor } = controller;
  const userList = useSelector((state) => state.users?.users || []);


  useEffect(() => {
    if (isEmpty(userList)) {
      dispatch(getUsers());
    }
  }, [dispatch]);

  return (
    <>
      <MDBox>
        <DashboardLayout>
          <DashboardNavbar />
          <MDBox pt={2} pb={3}>
            <Grid container spacing={6}>
              <Grid item xs={12}>
                <Card>
                  <MDBox
                    mx={1}
                    mt={-2}
                    py={1}
                    px={1}
                    variant="gradient"
                    bgColor={sidenavColor}
                    borderRadius="lg"
                    coloredShadow={sidenavColor}
                    className="d-flex align-items-center gap-2"
                  >
                    <MDTypography
                      variant="h6"
                      color="white"
                      className="flex-grow-1"
                    >
                      Users List
                    </MDTypography>
                  </MDBox>

                  <MDBox pt={3}>
                    <UserTable userData={userList} />
                  </MDBox>
                </Card>
              </Grid>
            </Grid>
          </MDBox>
          <Footer />
        </DashboardLayout>
      </MDBox>
    </>
  );
}

export default MyUsers;
