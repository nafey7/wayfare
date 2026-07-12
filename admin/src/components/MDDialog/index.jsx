import { forwardRef } from "react";

// prop-types is a library for typechecking of props
import PropTypes from "prop-types";

// Custom styles for MDInput
import MDDialogRoot from "components/MDDialog/MDDialogRoot";

const MDDialog = forwardRef(({ error, success, disabled, ...rest }, ref) => (
  <MDDialogRoot {...rest} ref={ref} ownerState={{ error, success, disabled }} />
));

// Setting default values for the props of MDDialog
MDDialog.defaultProps = {
  error: false,
  success: false,
  disabled: false,
};

// Typechecking props for the MDDialog
MDDialog.propTypes = {
  error: PropTypes.bool,
  success: PropTypes.bool,
  disabled: PropTypes.bool,
};

export default MDDialog;
