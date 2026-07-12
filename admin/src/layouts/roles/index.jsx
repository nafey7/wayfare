import { useEffect, useState } from "react";
import Card from "@mui/material/Card";
import Grid from "@mui/material/Grid";
import MDBox from "components/MDBox";
import MDButton from "components/MDButton";
import MDTypography from "components/MDTypography";
import Footer from "examples/Footer";
import DashboardLayout from "examples/LayoutContainers/DashboardLayout";
import DashboardNavbar from "examples/Navbars/DashboardNavbar";
import { useMaterialUIController } from "context";
import CreateRoles from "./components/CreateRoles";
import RolesTable from "./components/RolesTable";
import { getRoles } from "store/slice/roles/roleSlice";
import { useDispatch, useSelector } from "react-redux";
import { isEmpty } from "lodash";
import { FormControl } from "@mui/material";
import RolesSearchBar from "./components/RolesSearchBar";

const Roles = () => {
  const dispatch = useDispatch();
  const [controller] = useMaterialUIController();
  const { sidenavColor } = controller;
  const [dialogOpen, setDialogOpen] = useState(false);
  const [filteredRoles, setFilteredRoles] = useState([]);
  const rolesList = useSelector((state) => state.roles.rolesList || []);
  const loading = useSelector((state) => state.roles.loading || false);

  const userData = useSelector((state) => state.users?.meInfo);
  const roleModules = userData?.roleModules || {};

  useEffect(() => {
    if (isEmpty(rolesList)) {
      dispatch(getRoles());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch]);

  const updateData = async () => {
    await dispatch(getRoles());
  };

  return (
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
                className="d-flex align-items-center justify-content-between"
              >
                <MDTypography variant="h6" color="white">
                  Roles
                </MDTypography>
                {roleModules.Role_add && (
                  <MDButton
                    variant="outlined"
                    size="small"
                    onClick={() => setDialogOpen(true)}
                  >
                    Add New Role
                  </MDButton>
                )}
              </MDBox>
              <MDBox mx={3} pt={3} display="flex" justifyContent="flex-end">
                <FormControl>
                  <RolesSearchBar
                    rolesList={rolesList}
                    setFilteredRoles={setFilteredRoles}
                  />
                </FormControl>
              </MDBox>
              <MDBox pt={3}>
                <RolesTable
                  loading={loading}
                  rolesData={!isEmpty(filteredRoles) ? filteredRoles : []}
                  updateParentData={updateData}
                />
                <CreateRoles
                  dialogOpen={dialogOpen}
                  onClose={() => {
                    setDialogOpen(false);
                  }}
                  updateParentData={updateData}
                  userRole={userData.roleLevel}
                />
              </MDBox>
            </Card>
          </Grid>
        </Grid>
      </MDBox>
      <Footer />
    </DashboardLayout>
  );
};

export default Roles;
