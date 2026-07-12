// @mui material components
import Grid from "@mui/material/Grid";
import Divider from "@mui/material/Divider";
// PMS components
import MDBox from "components/MDBox";
// PMS example components
import DashboardLayout from "examples/LayoutContainers/DashboardLayout";
import DashboardNavbar from "examples/Navbars/DashboardNavbar";
import Footer from "examples/Footer";
import ProfileInfoCard from "examples/Cards/InfoCards/ProfileInfoCard";
import { useDispatch, useSelector } from "react-redux";
// Overview page components
import Header from "layouts/profile/components/Header";
import { get, isEmpty } from "lodash";
import { useEffect } from "react";
// import { setUserData } from "store/slice/auth/authSlice";
// import { getUserInfo } from "store/slice/auth/authSlice";

function Overview() {
  const dispatch = useDispatch();
  const userData = useSelector((state) => get(state, "users.meInfo", {}));

  // useEffect(() => {
  //   if (isEmpty(userData)) {
  //     handleGetUser();
  //   }
  // // eslint-disable-next-line react-hooks/exhaustive-deps
  // }, []);

  // const handleGetUser = async () => {
  //   try {
  //     const response = await dispatch(getUserInfo()).unwrap();
  //     if (response?.success) {
  //       const user = response?.data;
  //       dispatch(setUserData(user));
  //     }
  //   } catch (error) {
  //     console.error("Error getting places:", error);
  //   }
  // };
  return (
    <DashboardLayout>
      <DashboardNavbar />
      <MDBox mb={2} />
      <Header userData={userData}>
        <MDBox mt={5} mb={3}>
          <Grid container spacing={1}>
            <Grid item xs={12} md={12} xl={12} sx={{ display: "flex" }}>
              <Divider orientation="vertical" sx={{ ml: -2, mr: 1 }} />
              <ProfileInfoCard
                title="profile information"
                info={{
                  mobile: userData.mobile || "123456789",
                  email: userData.email || "example@example.com",
                }}
                social={
                  [
                    // {
                    //   link: "https://www.facebook.com/CreativeTim/",
                    //   icon: <FacebookIcon />,
                    //   color: "facebook",
                    // },
                  ]
                }
                action={{ route: "", tooltip: "Password Reset" }}
                shadow={false}
              />
              <Divider orientation="vertical" sx={{ mx: 0 }} />
            </Grid>
          </Grid>
        </MDBox>
      </Header>
      <Footer />
    </DashboardLayout>
  );
}

export default Overview;
