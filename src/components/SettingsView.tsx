
import * as React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom'
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';

import * as _GridList from 'material-ui/GridList';
let GridList = _GridList.default;
console.log(_GridList)
let GridListTile = _GridList.GridListTile;

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
            newColor: "#000"
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
                <SketchPicker color={this.props.color}
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
    colorPickerOpen: boolean
}

class SettingsView extends React.Component<ISettingsViewProps,ISettingsViewState> {

  constructor(props) {
    super(props);

    this.state = {
        palette: {
            type:props.theme.palette.type
        },
        colorPickerOpen: false,
    }
    this.updateStyle = this.updateStyle.bind(this);
    this.onThemeTypeSwitch = this.onThemeTypeSwitch.bind(this);
    this.showColorPicker = this.showColorPicker.bind(this);
    this.hideColorPicker = this.hideColorPicker.bind(this);
    this.setNewColor = this.setNewColor.bind(this);
  }

  public updateStyle(state) {
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
    this.setState({colorPickerOpen: true});
  }

  public setNewColor(color) {
    this.setState({colorPickerOpen: false});
  }

  public hideColorPicker() {
    this.setState({colorPickerOpen: false});
  }

  public render() {
    let cc = makeColor("#123456", this.state.palette.theme);

    return (
    <div>
    hello world

    <Switch
        checked={this.state.palette.type==="light"}
        onChange={this.onThemeTypeSwitch}
        aria-label="checkedA"
        />
    <ColorDisplay color={cc}/>
    <Button onClick={this.showColorPicker}>Open simple dialog</Button>
    <ColorDialog onCommit={this.setNewColor}
                 onCancel={this.hideColorPicker}
                 open={this.state.colorPickerOpen}
                 color="#FF0000"
    />

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
