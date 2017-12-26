
import * as React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom'
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';

import * as _GridList from 'material-ui/GridList';
let GridList = _GridList.default;
console.log(_GridList)
let GridListTile = _GridList.GridListTile;
import Grid from 'material-ui/Grid';

import * as UiList  from 'material-ui/List';
const List = UiList.default
const ListItem = UiList.ListItem
const ListItemIcon = UiList.ListItemIcon
const ListItemText = UiList.ListItemText
const ListItemSecondaryAction = UiList.ListItemSecondaryAction
import IconButton from 'material-ui/IconButton';
import Send from 'material-ui-icons/Send';
import Delete from 'material-ui-icons/Delete';
import MoreVert from 'material-ui-icons/MoreVert';
import ColorLens from 'material-ui-icons/ColorLens';

import * as themeActionCreators from '../actions/theme';
let actionCreators = Object.assign({}, themeActionCreators);

import Typography from 'material-ui/Typography';

import History from '../history';

import * as UiCard from 'material-ui/Card';
const Card = UiCard.default;

import Switch from 'material-ui/Switch';
import Dialog, { DialogTitle } from 'material-ui/Dialog';
import { SketchPicker } from 'react-color';
import Button from 'material-ui/Button';

import {
    makeColor
} from '../utils/theme'

export interface IColorDisplayProps {
    color: any
}
export interface IColorDisplayState {

}

class ColorDisplay extends React.Component<IColorDisplayProps,IColorDisplayState> {

    public render() {
        let cc = this.props.color
        let fields = ['50', '100', '200', '300', '400',
                '500', '600', '700', '800', '900',
                'A100', 'A200', 'A400', 'A700']
        return (
            <GridList cols={7} cellHeight={40}>
            {fields.map( (field) => {
                return <GridListTile key={field} cols={1}>
                        <div style={{
                            width:"100%",
                            height:"100%",
                            backgroundColor:cc[field],
                            textAlign:"center",
                            verticalAlign: "middle",
                            lineHeight: "40px"}}>
                            <div style={{
                                filter:"invert(100%)",
                                color:cc[field]}}>
                            {field}
                            </div>
                        </div>
                       </GridListTile>
            })}
            </GridList>
        );
    }
}

export interface IColorDialogProps {
    onCommit: (color) => void,
    onCancel: () => void,
    color: string,
    open: boolean,
}

export interface IColorDialogState {
    newColor: string
}

class ColorDialog extends React.Component<IColorDialogProps,IColorDialogState> {

    constructor(props) {
        super(props);
        this.state = {
            newColor: props.color
        }
        this.onColorChanged = this.onColorChanged.bind(this);
    }

    public onColorChanged(color) {
        this.setState({ newColor: color.hex });
    }

    public render() {
        return (
            <Dialog
                    open={this.props.open}
                >
                <DialogTitle>Select Color</DialogTitle>
                <SketchPicker color={this.state.newColor}
                              onChangeComplete={this.onColorChanged} />
                <Button onClick={() => {this.props.onCommit(this.state.newColor)}}>
                    commit changes
                </Button>
            </Dialog>
        );
    }
}

export interface ISettingsViewProps {
    theme: any,
    children?: any,
    setTheme: (theme) => any,
    setPalette: (theme) => any,
}

export interface ISettingsViewState {
    palette: any,
    colorPickerOpen: boolean,
    colorPickerTarget: string,
}

class SettingsView extends React.Component<ISettingsViewProps,ISettingsViewState> {

  constructor(props) {
    super(props);

    let palette = {
        type: props.theme.palette.type,
        primary: props.theme.palette.primary,
        secondary: props.theme.palette.secondary,
    }
    this.state = {
        palette: palette,
        colorPickerOpen: false,
        colorPickerTarget: "",
    }
    this.updateStyle = this.updateStyle.bind(this);
    this.onThemeTypeSwitch = this.onThemeTypeSwitch.bind(this);
    this.showColorPicker = this.showColorPicker.bind(this);
    this.hideColorPicker = this.hideColorPicker.bind(this);
    this.setNewColor = this.setNewColor.bind(this);
  }

  public updateStyle(state) {
    console.log(state)
    this.props.setPalette(state.palette);
  }

  public onThemeTypeSwitch(event, checked) {
    let palette = Object.assign({},this.state.palette);
    palette.type = (checked?"light":"dark");
    this.updateStyle({
        palette: palette,
    });
  }

  public showColorPicker(target) {
    this.setState({colorPickerOpen: true,
                   colorPickerTarget: target});
  }

  public setNewColor(color) {
    this.setState({colorPickerOpen: false});
    let palette = Object.assign({},this.state.palette);
    if (this.state.colorPickerTarget === "primary") {
        palette.primary = makeColor(color, this.state.palette.type)
        this.updateStyle({
            palette: palette,
        });
    } else if (this.state.colorPickerTarget === "secondary") {
        palette.secondary = makeColor(color, this.state.palette.type)
        this.updateStyle({
            palette: palette,
        });
    }

  }

  public hideColorPicker() {
    this.setState({colorPickerOpen: false});
  }

  public render() {

    return (
    <div>
    <ColorDialog onCommit={this.setNewColor}
                 onCancel={this.hideColorPicker}
                 open={this.state.colorPickerOpen}
                 color="#FF0000" />

    {this.state.palette.type}

    <Switch
        checked={this.state.palette.type==="light"}
        onChange={this.onThemeTypeSwitch}>
    </Switch>


    <Grid container spacing={24}>
        <Grid item  xs={1}>
            <div style={{
                width:"100%",
                height:"100%",
                textAlign:"center",
                verticalAlign: "middle",
                lineHeight: "80px"}}>
                <IconButton onClick={(e) => this.showColorPicker("primary")}>
                    <ColorLens />
                </IconButton>
            </div>
        </Grid>
        <Grid item  xs={11}>
            <ColorDisplay color={this.state.palette.primary}/>
        </Grid>
    </Grid>

    <Grid container spacing={24}>
        <Grid item  xs={1}>
            <div style={{
                width:"100%",
                height:"100%",
                textAlign:"center",
                verticalAlign: "middle",
                lineHeight: "80px"}}>
                <IconButton onClick={(e) => this.showColorPicker("secondary")}>
                    <ColorLens />
                </IconButton>
            </div>
        </Grid>
        <Grid item  xs={11}>
            <ColorDisplay color={this.state.palette.secondary}/>
        </Grid>
    </Grid>


    </div>
    )
  }

}

function mapStateToProps(state) {
  return {
    theme : state.theme.theme
  }
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators(actionCreators, dispatch);
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(SettingsView);
