// react-routers components
import { Link } from "react-router-dom";
import * as Yup from "yup";
// prop-types is library for typechecking of props
import PropTypes from "prop-types";

// @mui material components

// PMS components
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

// PMS base styles
import { useState } from "react";
import {
  Card,
  Icon,
  IconButton,
  DialogContent,
  Tooltip,
  Grid,
} from "@mui/material";
import MDDialog from "components/MDDialog";
import MDButton from "components/MDButton";
import { useMaterialUIController } from "context";
import MDInput from "components/MDInput";
import { Formik } from "formik";
import { passwordReset } from "store/slice/users/userSlice";
import { useDispatch } from "react-redux";
import CircularIndeterminate from "components/MDLoading";
import MDSnackbar from "components/MDSnackbar";

function ProfileInfoCard({ title, description, info, social, action, shadow }) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [controller] = useMaterialUIController();
  const { sidenavColor } = controller;
  const dispatch = useDispatch();
  const [notification, setNotification] = useState({
    color: "",
    icon: "",
    title: "",
    content: "",
    show: false,
    close: () => setNotification({ ...notification, show: false }),
  });

  const labels = [];
  const values = [];

  // Convert this form `objectKey` of the object key in to this `object key`
  Object.keys(info).forEach((el) => {
    if (el.match(/[A-Z\s]+/)) {
      const uppercaseLetter = Array.from(el).find((i) => i.match(/[A-Z]+/));
      const newElement = el.replace(
        uppercaseLetter,
        ` ${uppercaseLetter.toLowerCase()}`
      );

      labels.push(newElement);
    } else {
      labels.push(el);
    }
  });

  // Push the object values into the values array
  Object.values(info).forEach((el) => values.push(el));

  // Render the card info items
  const renderItems = labels.map((label, key) => (
    <MDBox key={label} display="flex" py={1} pr={2}>
      <MDTypography
        variant="button"
        fontWeight="bold"
        textTransform="capitalize"
      >
        {label}: &nbsp;
      </MDTypography>
      <MDTypography variant="button" fontWeight="regular" color="text">
        &nbsp;{values[key]}
      </MDTypography>
    </MDBox>
  ));
  const onClose = () => {
    setDialogOpen(false);
  };

  const handelPasswordReset = (payload) => {
    setIsLoading(true);
    dispatch(passwordReset(payload))
      .unwrap()
      .then((res) => {
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
  const passwordResetValidationSchema = Yup.object().shape({
    newPassword: Yup.string()
      .min(6, "Password min length 6 digits")
      .max(18, "Password is too long!")
      .required("Password is required!"),
  });

  return (
    <>
      <CircularIndeterminate
        type="full"
        size={20}
        text="Password Reset in process.. "
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
      <Card sx={{ height: "100%", boxShadow: !shadow && "none" }}>
        <MDBox
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          pt={2}
          px={2}
        >
          <MDTypography
            variant="h6"
            fontWeight="medium"
            textTransform="capitalize"
          >
            {title}
          </MDTypography>
          <MDTypography
            component={Link}
            to={action.route}
            variant="body2"
            color="secondary"
          >
            <Tooltip title={action.tooltip} placement="top">
              <IconButton color="success">
                <Icon fontSize="small" onClick={() => setDialogOpen(true)}>
                  password
                </Icon>
              </IconButton>
            </Tooltip>
          </MDTypography>
        </MDBox>
        <MDBox p={2}>
          <MDBox>
            {renderItems}
            <MDBox display="flex" py={1} pr={2}>
              <MDTypography
                variant="button"
                fontWeight="bold"
                textTransform="capitalize"
              ></MDTypography>
            </MDBox>
          </MDBox>
        </MDBox>

        <MDDialog
          dialogTitle="Password Reset"
          open={dialogOpen}
          dialogClose={onClose}
          closeIcon={true}
          maxWidth="sm"
        >
          <DialogContent>
            <Formik
              initialValues={{
                newPassword: "",
              }}
              validationSchema={passwordResetValidationSchema}
              onSubmit={(value, action) => {
                handelPasswordReset(value);
              }}
            >
              {(props) => (
                <form onSubmit={props.handleSubmit}>
                  <MDBox mt={2} mb={2}>
                    <Grid container spacing={2} className="">
                      <Grid item xs={12} md={8}>
                        <MDInput
                          type="password"
                          name="newPassword"
                          label="New Password"
                          value={props.values.newPassword}
                          onChange={props.handleChange}
                          onBlur={props.handleBlur}
                          error={
                            props.errors.newPassword && props.touched.newPassword
                              ? true
                              : false
                          }
                          success={
                            props.errors.newPassword && props.touched.newPassword
                              ? false
                              : true
                          }
                          helperText={
                            props.errors.newPassword && props.touched.newPassword
                              ? props.errors.newPassword
                              : null
                          }
                        />
                      </Grid>
                      <Grid item xs={12} md={4}>
                        <MDButton
                          color={sidenavColor}
                          variant="contained"
                          type="submit"
                        >
                          Submit
                        </MDButton>
                      </Grid>
                    </Grid>
                  </MDBox>
                </form>
              )}
            </Formik>
          </DialogContent>
        </MDDialog>
      </Card>
    </>
  );
}

// Setting default props for the ProfileInfoCard
ProfileInfoCard.defaultProps = {
  shadow: true,
};

// Typechecking props for the ProfileInfoCard
ProfileInfoCard.propTypes = {
  title: PropTypes.string.isRequired,
  description: PropTypes.string.isRequired,
  info: PropTypes.objectOf(PropTypes.string).isRequired,
  social: PropTypes.arrayOf(PropTypes.object).isRequired,
  action: PropTypes.shape({
    route: PropTypes.string.isRequired,
    tooltip: PropTypes.string.isRequired,
  }).isRequired,
  shadow: PropTypes.bool,
};

export default ProfileInfoCard;
