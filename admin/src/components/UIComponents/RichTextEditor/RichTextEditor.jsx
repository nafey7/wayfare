import React, { useEffect, useState } from "react";

import { useTheme } from "@mui/material/styles";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import FormHelperText from "@mui/material/FormHelperText";

import { isEmpty } from "lodash";
import { Editor } from "react-draft-wysiwyg";
import "react-draft-wysiwyg/dist/react-draft-wysiwyg.css";
import {
  EditorState,
  convertToRaw,
  convertFromHTML,
  ContentState,
} from "draft-js";
import draftjsToHtml from "draftjs-to-html";

import RGBColorChart from "./RGBColorChart.json";
import { purposeTags } from "global/constants";

const RichTextEditor = (props) => {
  const { label, name, value, setFieldValue, error, helperText, purpose="product" } = props;
  const theme = useTheme();
  const { palette } = theme;
  const { grey, error: colorError, success: colorSuccess } = palette;
  const blocksFromHTML = convertFromHTML(value);

  const state = ContentState.createFromBlockArray(
    blocksFromHTML.contentBlocks,
    blocksFromHTML.entityMap
  );

  const [editorState, setEditorState] = useState(() =>
    isEmpty(value)
      ? EditorState.createEmpty()
      : EditorState.createWithContent(state)
  );
  const [hasFocus, setHasFocus] = useState(false);
  const [mentionTags, setMentionTags] = useState([]);

  const onEditorStateChange = async (eData) => {
    setEditorState(eData);
    const data = draftjsToHtml(convertToRaw(eData.getCurrentContent()));
    setFieldValue(name, data);
    if (!eData.getCurrentContent().hasText()) {
      setFieldValue(name, "");
    }
  };

  const getBorder = () => {
    if (error) {
      return `1px solid ${colorError}`;
    } else if (hasFocus) {
      return `2px solid blue`;
    } else {
      return `1px solid ${grey[200]}`;
    }
  };

  useEffect(() => {
    setMentionTags(purposeTags[purpose ?? ""] ?? []);
  }, [purpose]);

  return (
    <>
      <FormControl error={error} fullWidth={true} variant="outlined">
        <InputLabel
          htmlFor="content-field"
          sx={{
            color: hasFocus ? colorSuccess.main : "inherit",
            top: "-20px",
            left: "-2px",
            padding: "1px 4px",
            fontSize: "0.875rem",
            backgroundColor: ({ palette }) => palette.background.paper,
          }}
        >
          {label}
        </InputLabel>
        <Editor
          toolbarHidden={false}
          name={name}
          editorState={editorState}
          onEditorStateChange={onEditorStateChange}
          onFocus={() => {
            setHasFocus(true);
          }}
          onBlur={() => {
            setHasFocus(false);
          }}
          wrapperClassName="wrapperClassName"
          editorClassName="editorClassName"
          toolbarClassName="toolbarClassName"
          wrapperStyle={{
            border: getBorder(),
            borderRadius: "6px",
            transition: "all .2s ease",
          }}
          editorStyle={{
            minHeight: "160px",
            maxHeight: "360px",
            margin: 0,
            padding: "8px 12px",
            borderBottomRightRadius: "4px",
            borderBottomLeftRadius: "4px",
            borderTop: getBorder(),
            transition: "all .2s ease",
          }}
          toolbarStyle={{
            marginTop: theme.spacing(0),
            marginBottom: theme.spacing(0),
            paddingTop: label ? theme.spacing(2) : theme.spacing(0.75),
            borderRadius: "inherit",
          }}
          toolbar={{
            options: [
              "inline",
              "blockType",
              "fontSize",
              "fontFamily",
              "list",
              "textAlign",
              "colorPicker",
              "link",
              "embedded",
              "emoji",
              "remove",
              "history",
            ],
            inline: { inDropdown: false },
            blockType: {
              inDropdown: true,
              options: [
                "Normal",
                "H1",
                "H2",
                "H3",
                "H4",
                "H5",
                "H6",
                "Blockquote",
                "Code",
              ],
              className: undefined,
              component: undefined,
              dropdownClassName: undefined,
            },
            fontSize: {
              inDropdown: true,
              options: [
                8, 9, 10, 11, 12, 14, 16, 18, 24, 30, 36, 48, 60, 72, 96,
              ],
            },
            colorPicker: {
              popupClassName: "custom_color_picker_model",
              colors: RGBColorChart,
              title: "Color Picker",
            },
            list: { inDropdown: false },
            textAlign: { inDropdown: true },
            link: { inDropdown: true },
            history: { inDropdown: true },
          }}
          mention={{
            separator: ' ',
            trigger: '{',
            suggestions: mentionTags?.map(tag => ({ text: tag, value: `{${tag}}}` })),
          }}
        />
        <FormHelperText error>{helperText}</FormHelperText>
      </FormControl>
    </>
  );
};

export default RichTextEditor;
