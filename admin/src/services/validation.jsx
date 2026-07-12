import * as Yup from "yup";

export const loginValidationSchema = Yup.object().shape({
  emailOrPhoneNumber: Yup.string()
    .email("Please enter valid Email")
    .required("Email is required!"),
  password: Yup.string()
    .min(6, "Password min length 6 digits")
    .max(18, "Password is too long!")
    .required("Password is required!"),
});

export const createUserValidationSchema = Yup.object().shape({
  firstName: Yup.string()
    .required("First Name is required!")
    .label("First Name"),
  lastName: Yup.string().required("Last Name is required!").label("Last Name"),
  email: Yup.string()
    .email("Please enter valid Email")
    .required("Email is required!"),
  mobile: Yup.string()
    .required()
    .label("Mobile is required!")
    .min(10, "Mobile number should be 10 digits")
    .max(15, "Mobile number should be 15 digits"),
  roleId: Yup.string().when("roleLevel", {
    is: (value) => value === 50,
    then: () => Yup.string().required("Role is required"),
    otherwise: () => Yup.string().nullable(),
  }),
});

export const createRolesValidationSchema = Yup.object().shape({
  title: Yup.string().required().label("Role Title"),
});
