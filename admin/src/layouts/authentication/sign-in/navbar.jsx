import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { AppBar, Toolbar, Box } from "@mui/material";
import logoLight from "assets/images/logo-light2.png";

const Navbar = () => {
  const [scrolled, setScrolled] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const appBarStyle = {
    backgroundColor: "rgba(122, 130, 208, 0.8)",
    transition: "all 0.5s",
    boxShadow: scrolled ? "0 2px 10px rgba(0,0,0,0.1)" : "none",
  };

  return (
    <AppBar position="fixed" style={appBarStyle}>
      <Toolbar sx={{ display: "flex", justifyContent: "space-between" }}>
        {/* Logo */}
        <Box
          component="img"
          src={logoLight}
          width="auto"
          height={30}
          alt="Logo"
          sx={{ cursor: "pointer" }}
        />
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
