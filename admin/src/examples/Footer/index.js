/**
=========================================================
* PMS - v2.2.0
=========================================================

* Product Page: https://www.creative-tim.com/product/material-dashboard-react
* Copyright 2023 Creative Tim (https://www.creative-tim.com)

Coded by www.creative-tim.com

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

// prop-types is a library for typechecking of props
import PropTypes from "prop-types";

// @mui material components
// import Link from "@mui/material/Link";
// import Icon from "@mui/material/Icon";

// PMS components
// import MDBox from "components/MDBox";
// import MDTypography from "components/MDTypography";

// PMS base styles
// import typography from "assets/theme/base/typography";

function Footer({ company, links }) {
  // const { href, name } = company;
  // const { size } = typography;

  // const renderLinks = () =>
  //   links.map((link) => (
  //     <MDBox key={link.name} component="li" px={2} lineHeight={1}>
  //       <Link href={link.href} target="_blank">
  //         <MDTypography variant="button" fontWeight="regular" color="text">
  //           {link.name}
  //         </MDTypography>
  //       </Link>
  //     </MDBox>
  //   ));

  // return (
  //   <MDBox
  //     width="100%"
  //     display="flex"
  //     flexDirection={{ xs: "column", lg: "row" }}
  //     justifyContent="space-between"
  //     alignItems="center"
  //     px={1.5}
  //   >
  //     <MDBox
  //       display="flex"
  //       justifyContent="center"
  //       alignItems="center"
  //       flexWrap="wrap"
  //       color="text"
  //       fontSize={size.sm}
  //       px={1.5}
  //     >
  //       &copy; {new Date().getFullYear()}, made with
  //       <MDBox fontSize={size.md} color="text" mb={-0.5} mx={0.25}>
  //         <Icon color="inherit" fontSize="inherit">
  //           favorite
  //         </Icon>
  //       </MDBox>
  //       by
  //       <Link href={href} target="_blank">
  //         <MDTypography variant="button" fontWeight="medium">
  //           &nbsp;{name}&nbsp;
  //         </MDTypography>
  //       </Link>
  //       for a better parking experience.
  //     </MDBox>
  //     <MDBox
  //       component="ul"
  //       sx={({ breakpoints }) => ({
  //         display: "flex",
  //         flexWrap: "wrap",
  //         alignItems: "center",
  //         justifyContent: "center",
  //         listStyle: "none",
  //         mt: 3,
  //         mb: 0,
  //         p: 0,

  //         [breakpoints.up("lg")]: {
  //           mt: 0,
  //         },
  //       })}
  //     >
  //       {renderLinks()}
  //     </MDBox>
  //   </MDBox>
  // );
  return (<div></div>)
}

// Setting default values for the props of Footer
Footer.defaultProps = {
  company: { href: "https://www.dock.bot/", name: "Dock" },
  links: [
    { href: "https://www.dock.bot/", name: "Dock" },
    { href: "https://www.dock.bot", name: "About Us" },
    { href: "https://www.dock.bot", name: "Blog" },
    { href: "https://www.dock.bot", name: "License" },
  ],
};

// Typechecking props for the Footer
Footer.propTypes = {
  company: PropTypes.objectOf(PropTypes.string),
  links: PropTypes.arrayOf(PropTypes.object),
};

export default Footer;
