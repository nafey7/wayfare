// import { useState } from "react";
// import { DialogContent, Grid, Autocomplete } from "@mui/material";
// import MDButton from "components/MDButton";
// import { useDispatch } from "react-redux";
// import MDDialog from "components/MDDialog";
// import MDInput from "components/MDInput";
// import MDSnackbar from "components/MDSnackbar";
// import { Formik } from "formik";
// import { createUserValidationSchema } from "services/validation";
// import { useMaterialUIController } from "context";
// import CircularIndeterminate from "components/MDLoading";
// import { createUsers, updateUser } from "store/slice/users/userSlice";
// import { getRoles } from "store/slice/roles/roleSlice";
// import { ROLE } from "../../../constants/index";

// const CreateUser = (props) => {
//   const dispatch = useDispatch();
//   const { editUserData, dialogOpen, onClose, updateParentData } = props;
//   const [controller] = useMaterialUIController();
//   const { sidenavColor } = controller;
//   const [isLoading, setIsLoading] = useState(false);
//   const [rolesData, setRolesData] = useState([]);

//   const [notification, setNotification] = useState({
//     color: "",
//     icon: "",
//     title: "",
//     content: "",
//     show: false,
//     close: () => setNotification({ ...notification, show: false }),
//   });

//   const handleGetRoles = () => {
//     dispatch(getRoles())
//       .unwrap()
//       .then((res) => {
//         if (res?.success) {
//           setRolesData(res?.roles || []);
//         }
//       })
//       .catch((err) => {
//         console.error("Error creating brand:", err);
//       });
//   };

//   useState(() => {
//     handleGetRoles();
//   }, []);

//   const handleCreateUser = (userData) => {
//     setIsLoading(true);
//     dispatch(createUsers(userData))
//       .unwrap()
//       .then((res) => {
//         const success = res?.success;
//         updateParentData();
//         setIsLoading(false);
//         setNotification({
//           ...notification,
//           color: success ? "success" : "error",
//           title: success ? "Success" : "Error",
//           content: res?.message,
//           icon: success ? "check" : "warning",
//           show: true,
//         });
//         if (success) {
//           console.log("res=>");
//           onClose();
//         }
//       })
//       .catch((err) => {
//         setIsLoading(false);
//         setNotification({
//           ...notification,
//           color: "error",
//           title: "Error",
//           content: err?.message,
//           icon: "warning",
//           show: true,
//         });
//       });
//   };

//   const handleUpdateUser = (userData) => {
//     setIsLoading(true);
//     dispatch(updateUser(userData))
//       .unwrap()
//       .then((res) => {
//         const success = res?.success;
//         updateParentData();
//         setIsLoading(false);
//         setNotification({
//           ...notification,
//           color: success ? "success" : "error",
//           title: success ? "Success" : "Error",
//           content: res?.message,
//           icon: success ? "check" : "warning",
//           show: true,
//         });
//         if (success) {
//           console.log("res=>");
//           onClose();
//         }
//       })
//       .catch((err) => {
//         setIsLoading(false);
//         setNotification({
//           ...notification,
//           color: "error",
//           title: "Error",
//           content: err?.message,
//           icon: "warning",
//           show: true,
//         });
//       });
//   };

//   return (
//     <>
//       <CircularIndeterminate
//         type="full"
//         size={20}
//         text={editUserData ? "Updating User.. " : "Creating User.. "}
//         open={isLoading}
//       />
//       <MDSnackbar
//         color={notification.color}
//         icon={notification.icon}
//         title={notification.title}
//         content={notification.content}
//         open={notification.show}
//         close={notification.close}
//         bgWhite
//       />
//       <MDDialog
//         dialogTitle={editUserData ? "Update User" : "Create User"}
//         open={dialogOpen}
//         dialogClose={onClose}
//         closeIcon={true}
//         maxWidth="sm"
//       >
//         <DialogContent>
//           <Formik
//             initialValues={{
//               userId: editUserData ? editUserData?._id : "",
//               firstName: editUserData ? editUserData?.firstName : "",
//               lastName: editUserData ? editUserData?.lastName : "",
//               email: editUserData ? editUserData?.email : "",
//               mobile: editUserData ? editUserData?.mobile : "",
//               roleId: editUserData ? editUserData?.roleId?._id : "",
//               roleLevel: ROLE.USER,
//             }}
//             validationSchema={createUserValidationSchema}
//             onSubmit={(value, action) => {
//               console.log("values", value);
//               if (!editUserData) {
//                 handleCreateUser(value);
//               } else {
//                 handleUpdateUser(value);
//               }
//             }}
//           >
//             {(props) => (
//               <form onSubmit={props.handleSubmit}>
//                 <Grid container spacing={2} className="mt-1">
//                   <Grid item xs={12} md={6}>
//                     <MDInput
//                       name="firstName"
//                       value={props.values.firstName}
//                       onChange={props.handleChange}
//                       onBlur={props.handleBlur}
//                       label="First Name"
//                       error={
//                         props.errors.firstName && props.touched.firstName
//                           ? true
//                           : false
//                       }
//                       success={
//                         props.errors.firstName && props.touched.firstName
//                           ? false
//                           : true
//                       }
//                       helperText={
//                         props.errors.firstName && props.touched.firstName
//                           ? props.errors.firstName
//                           : null
//                       }
//                     />
//                   </Grid>
//                   <Grid item xs={12} md={6}>
//                     <MDInput
//                       name="lastName"
//                       value={props.values.lastName}
//                       onChange={props.handleChange}
//                       onBlur={props.handleBlur}
//                       label="Last Name"
//                       error={
//                         props.errors.lastName && props.touched.lastName
//                           ? true
//                           : false
//                       }
//                       success={
//                         props.errors.lastName && props.touched.lastName
//                           ? false
//                           : true
//                       }
//                       helperText={
//                         props.errors.lastName && props.touched.lastName
//                           ? props.errors.lastName
//                           : null
//                       }
//                     />
//                   </Grid>
//                   <Grid item xs={12} md={6}>
//                     <MDInput
//                       name="email"
//                       value={props.values.email}
//                       onChange={props.handleChange}
//                       onBlur={props.handleBlur}
//                       disabled={editUserData}
//                       label="Email"
//                       error={
//                         props.errors.email && props.touched.email ? true : false
//                       }
//                       success={
//                         props.errors.email && props.touched.email ? false : true
//                       }
//                       helperText={
//                         props.errors.email && props.touched.email
//                           ? props.errors.email
//                           : null
//                       }
//                     />
//                   </Grid>{" "}
//                   <Grid item xs={12} md={6}>
//                     <MDInput
//                       name="mobile"
//                       value={props.values.mobile}
//                       onChange={props.handleChange}
//                       onBlur={props.handleBlur}
//                       disabled={editUserData}
//                       label="Mobile"
//                       error={
//                         props.errors.mobile && props.touched.mobile
//                           ? true
//                           : false
//                       }
//                       success={
//                         props.errors.mobile && props.touched.mobile
//                           ? false
//                           : true
//                       }
//                       helperText={
//                         props.errors.mobile && props.touched.mobile
//                           ? props.errors.mobile
//                           : null
//                       }
//                     />
//                   </Grid>
//                   <Grid item xs={12}>
//                     <Autocomplete
//                       options={rolesData}
//                       getOptionLabel={(option) => option.title ?? ""}
//                       renderOption={(props, option) => (
//                         <li {...props}>
//                           <div>{option.title}</div>
//                         </li>
//                       )}
//                       name="roleId"
//                       autoHighlight
//                       disableClearable
//                       size="small"
//                       value={
//                         rolesData.find(
//                           (option) => option._id === props.values.roleId
//                         ) || null
//                       }
//                       getOptionSelected={(option, value) =>
//                         option._id === value._id
//                       }
//                       onChange={(event, value) => {
//                         props.setFieldValue("roleId", value ? value._id : "");
//                       }}
//                       renderInput={(params) => (
//                         <MDInput
//                           label="Select Role"
//                           fullWidth
//                           inputProps={{
//                             ...params.inputProps,
//                             autoComplete: "new-password",
//                           }}
//                           value={
//                             props.values.roleId
//                               ? rolesData.find(
//                                   (option) => option._id === props.values.roleId
//                                 )?.title
//                               : ""
//                           }
//                           error={
//                             props.errors.roleId && props.touched.roleId
//                               ? true
//                               : false
//                           }
//                           helperText={
//                             props.errors.roleId && props.touched.roleId
//                               ? props.errors.roleId
//                               : null
//                           }
//                           {...params}
//                         />
//                       )}
//                     />
//                   </Grid>{" "}
//                   <Grid item xs={12} className="text-right">
//                     <MDButton
//                       color={sidenavColor}
//                       variant="contained"
//                       type="submit"
//                     >
//                       {editUserData ? "Update" : "Create"}
//                     </MDButton>
//                   </Grid>
//                 </Grid>
//               </form>
//             )}
//           </Formik>
//         </DialogContent>
//       </MDDialog>
//     </>
//   );
// };

// export default CreateUser;
