import * as React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom'
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';

import Button from 'material-ui/Button';

import Tabs, { Tab } from 'material-ui/Tabs';

import AppBar from 'material-ui/AppBar';

import Settings from 'material-ui-icons/Settings';
import LibraryMusic from 'material-ui-icons/LibraryMusic';
import * as ListIcons from 'material-ui-icons/List';
const ListIcon = ListIcons.default

import SoundView from "./player/SoundView"
import QueueView from "./QueueView"
import DomainView from "./DomainView"
import DomainArtistView from "./DomainArtistView"

import Grid from 'material-ui/Grid';

import { Route, Switch } from 'react-router-dom';

import History from '../history'

interface Dictionary<T> {
    [Key: string]: T;
}

export interface MainViewProps {
  logoutAndRedirect: PropTypes.func,
  userName: PropTypes.string,
};

export interface MainViewState {
  open: boolean,
  currentTabIndex: number,
}

const style : Dictionary<React.CSSProperties> = {
  header: {
    textAlign: "center",
  },
  header_content: {
    padding: "5px",
    color: "white"
  }

}

class MainView extends React.Component<MainViewProps,MainViewState> {

  constructor(props) {
    super(props);
    this.state = {open:true,
                  currentTabIndex: 0};
    this.logout = this.logout.bind(this)
    this.onTabIndexChange = this.onTabIndexChange.bind(this)
  }

  logout(e) {
      e.preventDefault();
      this.props.logoutAndRedirect();
      this.setState({
          open: false,
      });
  }

  onTabIndexChange(event, value) {
    this.setState({ currentTabIndex: value });
    if (value==0) {
      History.push("/main/queue");
    } else if (value==1) {
      History.push("/main/library");
    } else if (value==2) {
      History.push("/main/settings");
    }
  }

  render() {

    return (
      <div>

      <AppBar style={{ position: "fixed", height:"160px" }} >
        <div style={style.header}>
          <header style={style.header_content}>

            <SoundView/>
          </header>
          <br/>
        </div>
      </AppBar>
      <div style={{ paddingTop: 160 }}>

       <Button
            style={{ marginTop: 50 }}
            onClick={(e) => this.logout(e)}
            raised={true}
          >Logout</Button>

        <Tabs
            value={this.state.currentTabIndex}
            onChange={this.onTabIndexChange}
            fullWidth
            indicatorColor="accent"
            textColor="accent"
          >
          <Tab icon={<ListIcon />} label="Queue" />
          <Tab icon={<LibraryMusic />} label="Library" />
          <Tab icon={<Settings />} label="Settings" />
        </Tabs>

        <Switch>
        <Route path={`/main/queue`} component={QueueView}/>
        <Route exact path={`/main/library`} component={DomainView}/>
        <Route exact path={`/main/library/:artist`} component={DomainArtistView}/>
        <Route path={"/main"} render={() => (
          <h3>View Not Implemented</h3>
        )}/>
        </Switch>
      </div>

      </div>
    );
  }
}

function mapStateToProps(state) {
  return {
    };
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators({}, dispatch);
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(MainView);
