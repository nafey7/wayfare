// prop-types is library for typechecking of props
import PropTypes from "prop-types";

// @mui material components
import Card from "@mui/material/Card";
import Icon from "@mui/material/Icon";

// PMS components
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

function DefaultSortInfoCard({ color, icon, title, value }) {
  return (
    <Card>
      <MDBox
        p={1.5}
        display="flex"
        alignItems="center"
        justifyContent="between"
      >
        <MDBox
          display="grid"
          justifyContent="center"
          alignItems="center"
          bgColor={color}
          color="white"
          width="3rem"
          height="3rem"
          shadow="md"
          borderRadius="lg"
          variant="gradient"
        >
          <Icon fontSize="small">{icon}</Icon>
        </MDBox>
        <MDBox textAlign="end" lineHeight={1.25} flexGrow={1}>
          <MDTypography
            variant="caption"
            color="text"
            fontWeight="regular"
            textTransform="capitalize"
          >
            {title}
          </MDTypography>
          {value && (
            <MDTypography variant="h6" fontWeight="medium">
              {value}
            </MDTypography>
          )}
        </MDBox>
      </MDBox>
    </Card>
  );
}

// Setting default values for the props of DefaultInfoCard
DefaultSortInfoCard.defaultProps = {
  color: "info",
  value: "",
};

// Typechecking props for the DefaultSortInfoCard
DefaultSortInfoCard.propTypes = {
  color: PropTypes.oneOf([
    "primary",
    "secondary",
    "info",
    "success",
    "warning",
    "error",
    "dark",
  ]),
  icon: PropTypes.node.isRequired,
  title: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
};

export default DefaultSortInfoCard;
