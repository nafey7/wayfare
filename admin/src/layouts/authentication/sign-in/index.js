import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Formik } from "formik";
import { useDispatch } from "react-redux";

import Card from "@mui/material/Card";
import TextField from "@mui/material/TextField";
import Switch from "@mui/material/Switch";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import { Visibility, VisibilityOff } from "@mui/icons-material";

import MDSnackbar from "components/MDSnackbar";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDButton from "components/MDButton";
import BasicLayout from "layouts/authentication/components/BasicLayout";

import bgImage from "assets/images/background.png";
import { postLogin } from "store/slice/auth/authSlice";
import { getMeInfo } from "store/slice/users/userSlice";
import { useMaterialUIController } from "context";
import { loginValidationSchema } from "services/validation";
import Navbar from "./navbar";
import CircularIndeterminate from "components/MDLoading";

function Basic() {
  const navigate = useNavigate();
  const [controller] = useMaterialUIController();
  const { sidenavColor } = controller;
  const dispatch = useDispatch();

  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [notification, setNotification] = useState({
    color: "",
    icon: "",
    title: "",
    content: "",
    show: false,
  });

  // Helper Functions
  const togglePasswordVisibility = () => setShowPassword(!showPassword);
  const toggleRememberMe = () => setRememberMe(!rememberMe);
  const handleNotificationClose = () =>
    setNotification((prev) => ({ ...prev, show: false }));

  const handleLogin = (values) => {
    setIsLoading(true);
    dispatch(postLogin(values))
      .unwrap()
      .then((res) => {
        if (res?.success) {
          localStorage.setItem("Authorization", res?.token);
          dispatch(getMeInfo());
          navigate("/dashboard");
        } else {
          setNotification({
            color: "error",
            icon: "warning",
            title: "Error",
            content: res?.message,
            show: true,
          });
        }
      })
      .catch(() => {
        setNotification({
          color: "error",
          icon: "error",
          title: "Login Failed",
          content: "An unexpected error occurred. Please try again.",
          show: true,
        });
      })
      .finally(() => setIsLoading(false));
  };

  const renderInputField = (name, label, type = "text", props) => (
    <MDBox mb={2}>
      <TextField
        name={name}
        type={type}
        label={label}
        value={props.values[name]}
        onChange={props.handleChange}
        onBlur={props.handleBlur}
        error={Boolean(props.errors[name] && props.touched[name])}
        helperText={props.touched[name] ? props.errors[name] : ""}
        fullWidth
        InputProps={
          name === "password"
            ? {
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={togglePasswordVisibility} edge="end">
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }
            : null
        }
      />
    </MDBox>
  );

  return (
    <BasicLayout image={bgImage}>
      <Navbar />
      <Formik
        initialValues={{
          emailOrPhoneNumber: "",
          password: "",
          isSignup: false,
          isPhoneNumber: false,
          isAdmin: true,
        }}
        validationSchema={loginValidationSchema}
        onSubmit={handleLogin}
      >
        {(props) => (
          <form onSubmit={props.handleSubmit}>
            <Card>
              <MDBox pt={4} pb={1} px={3}>
                {renderInputField(
                  "emailOrPhoneNumber",
                  "Email",
                  "emailOrPhoneNumber",
                  props
                )}
                {renderInputField(
                  "password",
                  "Password",
                  showPassword ? "text" : "password",
                  props
                )}
                <MDBox display="flex" alignItems="center" ml={-1}>
                  <Switch checked={rememberMe} onChange={toggleRememberMe} />
                  <MDTypography
                    variant="button"
                    sx={{ cursor: "pointer", ml: -1 }}
                    onClick={toggleRememberMe}
                  >
                    &nbsp;Remember me
                  </MDTypography>
                </MDBox>
                <MDBox mt={4}>
                  <MDButton
                    type="submit"
                    color={sidenavColor}
                    fullWidth
                    loading={true}
                  >
                    Sign in
                  </MDButton>
                </MDBox>
              </MDBox>
            </Card>
          </form>
        )}
      </Formik>
      <CircularIndeterminate type="full" size={20} text="" open={isLoading} />
      <MDSnackbar {...notification} close={handleNotificationClose} />
    </BasicLayout>
  );
}

export default Basic;
