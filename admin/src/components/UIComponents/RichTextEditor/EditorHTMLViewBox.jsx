import React from "react";
import Box from "@mui/material/Box";
import { styled } from "@mui/material";
import DOMPurify from "dompurify";

const createMarkup = (value) => {
  return {
    __html: DOMPurify.sanitize(value, { SAFE_FOR_TEMPLATES: true }),
  };
};

const EditorBox = styled(Box)(({ theme }) => ({
  "& > *,h1 ,h2 ,h3 ,h4 ,h5 ,h6 ,p,span,p>span": {
    fontFamily: "inherit !important",
  },
  "& > h1 ,h2 ,h3 ,h4 ,h5 ,h6 ,p": {
    marginBlockStart: theme.spacing(1),
    marginBlockEnd: theme.spacing(1),
  },
  "& > ul, ol": {
    marginBlockStart: theme.spacing(1),
    marginBlockEnd: theme.spacing(1),
    paddingInlineStart: theme.spacing(3),
  },
  "& code": {
    fontFamily:
      'SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
    backgroundColor: theme.palette.primary[50],
    paddingInline: theme.spacing(0.5),
    paddingBlock: theme.spacing(0.25),
    borderRadius: theme.spacing(0.5),
  },
}));

const EditorHTMLViewBox = ({ data, ...rest }) => {
  return (
    <EditorBox
      component="div"
      dangerouslySetInnerHTML={createMarkup(data)}
      className="editor-html-style "
      {...rest}
    />
  );
};

export default EditorHTMLViewBox;
