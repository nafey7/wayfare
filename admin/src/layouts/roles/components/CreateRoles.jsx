import { DialogContent, Grid } from "@mui/material";
import MDButton from "components/MDButton";
import { useState } from "react";
import MDDialog from "components/MDDialog";
import MDInput from "components/MDInput";
import MDSnackbar from "components/MDSnackbar";
import { Formik } from "formik";
import { createRolesValidationSchema } from "services/validation";
import { useMaterialUIController } from "context";
import { createRole } from "store/slice/roles/roleSlice";
import { useDispatch } from "react-redux";
import CircularIndeterminate from "components/MDLoading";
import UsersPermissionCard from "./PermissionCards/MyUsersPermissionCard";
import RolePermissionCard from "./PermissionCards/RolePermissionCard";
import ProfilePermissionCard from "./PermissionCards/ProfilePermissionCard";
import DashboardPermissionCard from "./PermissionCards/DashboardPermissionCard";
import ProductPermissionCard from "./PermissionCards/ProductPermissionCard";
import CategoryPermissionCard from "./PermissionCards/CategoryPermissionCard";
import BotPermissionCard from "./PermissionCards/BotsPermissionCard";
import ContentPermissionCard from "./PermissionCards/ContentBuilderPermissionCard";

const CreateRoles = (props) => {
  const dispatch = useDispatch();

  const { dialogOpen, onClose, updateParentData, userRole } = props;
  const [controller] = useMaterialUIController();
  const { sidenavColor } = controller;
  const [isLoading, setIsLoading] = useState(false);
  const [modules, setModules] = useState({});
  const [notification, setNotification] = useState({
    color: "",
    icon: "",
    title: "",
    content: "",
    show: false,
    close: () => setNotification({ ...notification, show: false }),
  });

  const handleCreateRole = (roleData) => {
    setIsLoading(true);
    dispatch(createRole(roleData))
      .unwrap()
      .then((res) => {
        console.log("Role creation response:", res);
        const success = res?.success;
        setIsLoading(false);
        setNotification({
          ...notification,
          color: success ? "success" : "error",
          title: success ? "Success" : "Error",
          content: res?.message,
          icon: success ? "check" : "warning",
          show: true,
        });
        if (success) {
          setModules({});
          updateParentData();
          onClose();
        }
      })
      .catch((err) => {
        console.error("Error creating brand:", err);
        setIsLoading(false);
        setNotification({
          ...notification,
          color: "error",
          title: "Error",
          content: err?.message,
          icon: "warning",
          show: true,
        });
      });
  };

  console.log("userRole ===>", userRole);
  return (
    <>
      <CircularIndeterminate
        type="full"
        size={20}
        text="Creating role.. "
        open={isLoading}
      />
      <MDSnackbar
        color={notification.color}
        icon={notification.icon}
        title={notification.title}
        content={notification.content}
        open={notification.show}
        close={notification.close}
        bgWhite
      />
      <MDDialog
        dialogTitle="Create New Role"
        open={dialogOpen}
        dialogClose={onClose}
        closeIcon={true}
        maxWidth="sm"
      >
        <DialogContent>
          <Formik
            initialValues={{
              title: "",
            }}
            validationSchema={createRolesValidationSchema}
            onSubmit={(value, action) => {
              handleCreateRole({ ...value, modules });
            }}
          >
            {(props) => (
              <form onSubmit={props.handleSubmit}>
                <Grid container spacing={2} className="mt-1">
                  <Grid item xs={12}>
                    <MDInput
                      name="title"
                      value={props.values.title}
                      onChange={props.handleChange}
                      onBlur={props.handleBlur}
                      label="Role Title"
                      error={
                        props.errors.title && props.touched.title ? true : false
                      }
                      success={
                        props.errors.title && props.touched.title ? false : true
                      }
                      helperText={
                        props.errors.title && props.touched.title
                          ? props.errors.title
                          : null
                      }
                    />
                  </Grid>

                  <Grid item sx={{ width: "100%" }}>
                    <DashboardPermissionCard
                      modules={modules}
                      setModules={setModules}
                    />
                  </Grid>
                  <Grid item sx={12}>
                    <RolePermissionCard
                      modules={modules}
                      setModules={setModules}
                    />
                  </Grid>
                  <Grid item sx={12}>
                    <UsersPermissionCard
                      modules={modules}
                      setModules={setModules}
                    />
                  </Grid>
                  <Grid item sx={{ width: "100%" }}>
                    <CategoryPermissionCard
                      modules={modules}
                      setModules={setModules}
                    />
                  </Grid>
                  <Grid item sx={{ width: "100%" }}>
                    <ProductPermissionCard
                      modules={modules}
                      setModules={setModules}
                    />
                  </Grid>
                  <Grid item sx={{ width: "100%" }}>
                    <BotPermissionCard
                      modules={modules}
                      setModules={setModules}
                    />
                  </Grid>
                  <Grid item sx={{ width: "100%" }}>
                    <ContentPermissionCard
                      modules={modules}
                      setModules={setModules}
                    />
                  </Grid>
                  <Grid item sx={{ width: "100%" }}>
                    <ProfilePermissionCard
                      modules={modules}
                      setModules={setModules}
                    />
                  </Grid>

                  <Grid item xs={12} className="text-right">
                    <MDButton
                      color={sidenavColor}
                      variant="gradient"
                      type="submit"
                    >
                      Create
                    </MDButton>
                  </Grid>
                </Grid>
              </form>
            )}
          </Formik>
        </DialogContent>
      </MDDialog>
    </>
  );
};

export default CreateRoles;
